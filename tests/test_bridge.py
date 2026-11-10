import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from foundation_robotics.tools import BOUNDARY, TOOL_NAMES, input_sha256
from foundation_robotics_bridge.schemas import tool_definitions
from foundation_robotics_bridge import server
from foundation_robotics_bridge.server import LIMITS, PROTOCOL, Bridge, encode_response

ROOT = Path(__file__).resolve().parents[1]
INIT = {"jsonrpc": "2.0", "id": "init", "method": "initialize", "params": {"protocolVersion": PROTOCOL}}
SQUEEZE = {"frames": [{"scale_permille": [1180, 780, 1180]}]}


def session(*frames, argv=()):
    raw = b"".join((f if type(f) is bytes else json.dumps(f).encode()) + b"\n" for f in frames)
    proc = subprocess.run([sys.executable, "-B", "-m", "foundation_robotics_bridge", *argv], cwd=ROOT, input=raw,
                          capture_output=True, timeout=30)
    return proc, [json.loads(line) for line in proc.stdout.splitlines()]


def call(arguments, name="squash_check", ident=1):
    return {"jsonrpc": "2.0", "id": ident, "method": "tools/call", "params": {"name": name, "arguments": arguments}}


class BridgeTests(unittest.TestCase):
    def test_handshake_catalog_and_a_verdict_with_evidence(self):
        proc, (hello, catalog, judged) = session(INIT, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                                                 call(SQUEEZE))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual((hello["result"]["protocolVersion"], hello["result"]["mcpCompatible"]), (PROTOCOL, False))
        self.assertEqual(catalog["result"]["tools"], tool_definitions())
        self.assertEqual(tuple(t["name"] for t in catalog["result"]["tools"]), TOOL_NAMES)
        result = judged["result"]
        receipt = result["structuredContent"]["receipt"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["assessment"], "thresholds_not_met")
        self.assertEqual((receipt["boundary"], receipt["status"], receipt["result"]["frames"][0]["volume_permille"]),
                         (BOUNDARY, "ok", 1086))
        self.assertEqual(receipt["input_sha256"], input_sha256(SQUEEZE))
        self.assertEqual({e["evidence"]["status"] for e in receipt["evidence"]}, {"RECORDED", "CHECK"})

    def test_bad_arguments_are_a_tool_error_that_still_carries_evidence(self):
        for arguments in ({}, {"frames": []}, {"frames": [{"scale_permille": [1, 2]}]}, {**SQUEEZE, "extra": 1}):
            _, (_, reply) = session(INIT, call(arguments))
            result = reply["result"]
            self.assertTrue(result["isError"], arguments)
            self.assertEqual(result["structuredContent"]["receipt"]["status"], "error")
            self.assertTrue(result["structuredContent"]["receipt"]["evidence"])

    def test_wire_profile_fails_closed(self):
        for frame, code in ((b'{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}', -32700),
                            (b'{"jsonrpc":"2.0","id":1,"method":"ping","x":1.5}', -32700),
                            (b'{"jsonrpc":"2.0","id":1,"method":"ping","x":NaN}', -32700),
                            (b"[" * 33 + b"]" * 33, -32002)):
            _, (_, reply) = session(INIT, frame)
            self.assertEqual(reply["error"]["code"], code, frame)
        _, (reply,) = session(call(SQUEEZE))
        self.assertEqual(reply["error"]["code"], -32000)
        _, (_, reply) = session(INIT, call({}, name="drive_motor"))
        self.assertEqual(reply["error"]["code"], -32602)
        proc, _ = session(INIT, argv=("--root", "/"))
        self.assertEqual(proc.returncode, 2)

    def test_gap_rob_05_an_oversized_or_unterminated_line_gets_one_reply_then_exit_status_2(self):
        ping = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping"}).encode()
        at_cap = ping[:-1] + b" " * (LIMITS["inputFrameBytes"] - len(ping)) + b"}"
        over_cap = at_cap[:-1] + b" }"
        proc, replies = session(at_cap, over_cap, ping)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(replies[0], {"jsonrpc": "2.0", "id": 7, "result": {}})
        self.assertEqual(len(replies), 2, replies)
        self.assertEqual((replies[1]["id"], replies[1]["error"]["code"]), (None, -32002))
        self.assertNotIn("result", replies[1])
        raw = ping + b"\n" + ping
        proc = subprocess.run([sys.executable, "-B", "-m", "foundation_robotics_bridge"], cwd=ROOT, input=raw,
                              capture_output=True, timeout=30)
        replies = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(len(replies), 2, replies)
        self.assertEqual(replies[0]["result"], {})
        self.assertEqual((replies[1]["id"], replies[1]["error"]["code"]), (None, -32002))
        proc, replies = session(ping)
        self.assertEqual((proc.returncode, len(replies)), (0, 1))

    def test_source_manifest_lists_every_file(self):
        manifest = json.loads((ROOT / "SOURCE-MANIFEST.json").read_text())["files"]
        actual = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(ROOT.rglob("*")) if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts
                  and p.relative_to(ROOT).parts[0] != ".github" and p.suffix != ".pyc" and p.name != "SOURCE-MANIFEST.json"}
        self.assertEqual(manifest, actual, "run: python -B tools/build_manifest.py, then re-pin the adapter")


def frame(message):
    return json.dumps(message, separators=(",", ":")).encode()


def padded(message, size):
    raw = frame(message)
    return raw[:-1] + b" " * (size - len(raw)) + b"}"


def ready():
    bridge = Bridge()
    if "result" not in bridge.handle(frame(INIT)):
        raise AssertionError("initialize failed")
    return bridge


class BridgeGapTests(unittest.TestCase):
    def assertWire(self, reply, code, identifier=None):
        self.assertEqual((reply["id"], reply["error"]["code"]), (identifier, code), reply)
        self.assertNotIn("result", reply)

    def test_gap_rob_01_input_frames_over_65536_bytes_are_rejected_with_32002(self):
        ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        at_cap = padded(ping, LIMITS["inputFrameBytes"])
        self.assertEqual(len(at_cap), 65536)
        self.assertEqual(Bridge().handle(at_cap), {"jsonrpc": "2.0", "id": 1, "result": {}})
        self.assertWire(Bridge().handle(padded(ping, 65537)), -32002)

    def test_gap_rob_02_more_than_16384_json_nodes_are_rejected_with_32002(self):
        self.assertWire(Bridge().handle(frame([0] * 16383)), -32600)
        self.assertWire(Bridge().handle(frame([0] * 16384)), -32002)
        nested = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": "squash_check", "arguments": {"frames": [0] * 16384}}}
        self.assertLessEqual(len(frame(nested)), LIMITS["inputFrameBytes"])
        self.assertWire(ready().handle(frame(nested)), -32002)

    def test_gap_rob_03_strings_over_1024_characters_are_rejected_with_32002(self):
        def request(method="ping", key="x"):
            return frame({"jsonrpc": "2.0", "id": 1, "method": method, "params": {key: 0}})
        self.assertWire(Bridge().handle(request("m" * 1024)), -32601, 1)
        self.assertWire(Bridge().handle(request("m" * 1025)), -32002)
        self.assertWire(Bridge().handle(request(key="k" * 1024)), -32602, 1)
        self.assertWire(Bridge().handle(request(key="k" * 1025)), -32002)
        self.assertWire(Bridge().handle(request(key="é" * 1025)), -32002)

    def test_gap_rob_04_integers_over_15_digits_are_rejected_with_32002(self):
        for identifier in (10 ** 14, 10 ** 15 - 1, -(10 ** 15 - 1)):
            self.assertEqual(Bridge().handle(frame({"jsonrpc": "2.0", "id": identifier, "method": "ping"})),
                             {"jsonrpc": "2.0", "id": identifier, "result": {}})
        for identifier in (10 ** 15, -(10 ** 15), 10 ** 30):
            self.assertWire(Bridge().handle(frame({"jsonrpc": "2.0", "id": identifier, "method": "ping"})), -32002)
        self.assertWire(ready().handle(frame(call({"frames": [{"scale_permille": [10 ** 15, 1000, 1000]}]}))),
                        -32002)

    def test_gap_rob_06_a_response_over_1048576_bytes_is_withheld_with_32002(self):
        def reply(size):
            body = {"jsonrpc": "2.0", "id": 9, "result": {"blob": ""}}
            body["result"]["blob"] = "x" * (size - len(encode_response(body)) + 1)
            return body
        fits = reply(LIMITS["outputFrameBytes"])
        raw = encode_response(fits)
        self.assertEqual(len(raw) - 1, 1048576)
        self.assertEqual(json.loads(raw), fits)
        raw = encode_response(reply(LIMITS["outputFrameBytes"] + 1))
        self.assertLess(len(raw), 1024)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(json.loads(raw), {"jsonrpc": "2.0", "id": 9,
                                           "error": {"code": -32002, "message": "Result withheld"}})

    def test_gap_rob_07_ping_returns_empty_and_works_before_initialize(self):
        bridge = Bridge()
        self.assertEqual(bridge.handle(frame({"jsonrpc": "2.0", "id": "p", "method": "ping"})),
                         {"jsonrpc": "2.0", "id": "p", "result": {}})
        self.assertEqual(bridge.handle(frame({"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}})),
                         {"jsonrpc": "2.0", "id": 2, "result": {}})
        self.assertFalse(bridge.initialized)
        self.assertWire(bridge.handle(frame({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})), -32000, 3)
        self.assertWire(bridge.handle(frame({"jsonrpc": "2.0", "id": 4, "method": "ping", "params": {"x": 1}})),
                        -32602, 4)
        self.assertEqual(bridge.handle(frame(INIT))["result"]["protocolVersion"], PROTOCOL)
        self.assertEqual(bridge.handle(frame({"jsonrpc": "2.0", "id": 5, "method": "ping"}))["result"], {})

    def test_gap_rob_08_second_initialize_is_32000_and_wrong_protocol_is_32001(self):
        bridge = Bridge()
        for version in ("2024-11-05", "foundation-robotics-jsonrpc/2", 1):
            wrong = {**INIT, "id": "v", "params": {"protocolVersion": version}}
            self.assertWire(bridge.handle(frame(wrong)), -32001, "v")
        self.assertFalse(bridge.initialized)
        self.assertWire(bridge.handle(frame({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})), -32000, 1)
        self.assertIn("result", bridge.handle(frame(INIT)))
        self.assertWire(bridge.handle(frame({**INIT, "id": "again"})), -32000, "again")
        self.assertTrue(bridge.initialized)
        self.assertIn("result", bridge.handle(frame({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})))

    def test_gap_rob_09_a_notification_gets_no_reply_and_is_not_executed(self):
        bridge = Bridge()
        self.assertIsNone(bridge.handle(frame({"jsonrpc": "2.0", "method": "initialize",
                                               "params": {"protocolVersion": PROTOCOL}})))
        self.assertFalse(bridge.initialized)
        self.assertIsNone(bridge.handle(frame({"jsonrpc": "2.0", "method": "ping"})))
        bridge = ready()
        with mock.patch.object(server, "run", wraps=server.run) as tool:
            self.assertIsNone(bridge.handle(frame({"jsonrpc": "2.0", "method": "tools/call",
                                                   "params": {"name": "squash_check", "arguments": SQUEEZE}})))
            tool.assert_not_called()
            self.assertIn("result", bridge.handle(frame(call(SQUEEZE))))
            tool.assert_called_once()
        proc, replies = session({"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": PROTOCOL}},
                                {"jsonrpc": "2.0", "method": "ping"}, call(SQUEEZE, ident="after"))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(len(replies), 1, replies)
        self.assertWire(replies[0], -32000, "after")

    def test_gap_rob_10_envelope_method_and_argument_errors(self):
        good = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        for message in ([good], [], [good, good], "ping", 1, None, {**good, "extra": 1}, {**good, "result": {}},
                        {**good, "jsonrpc": "1.0"}, {**good, "jsonrpc": 2}, {"id": 1, "method": "ping"},
                        {**good, "method": ""}, {**good, "method": 5}, {"jsonrpc": "2.0", "id": 1},
                        {**good, "id": None}, {**good, "id": "i" * 129}, {**good, "id": True}, {**good, "id": [1]},
                        {**good, "id": {}}):
            self.assertWire(ready().handle(frame(message)), -32600)
        self.assertEqual(ready().handle(frame({**good, "id": "i" * 128}))["result"], {})
        for method in ("tools/run", "shutdown", "Ping", "initialize/", "resources/list"):
            self.assertWire(ready().handle(frame({**good, "method": method})), -32601, 1)
            self.assertWire(Bridge().handle(frame({**good, "method": method})), -32601, 1)
        for arguments in ([], "frames", 1, None, True, [SQUEEZE]):
            self.assertWire(ready().handle(frame(call(arguments))), -32602, 1)
        for params in ({"name": "squash_check"}, {"arguments": SQUEEZE}, [], {"name": 1, "arguments": SQUEEZE},
                       {"name": "squash_check", "arguments": SQUEEZE, "x": 1}):
            self.assertWire(ready().handle(frame({**good, "method": "tools/call", "params": params})), -32602, 1)

    def test_gap_rob_11_an_unexpected_tool_exception_returns_32603_with_no_result(self):
        bridge = ready()
        for problem in (RuntimeError("boom"), KeyError("frames"), ZeroDivisionError(), TypeError("x")):
            with mock.patch.object(server, "run", side_effect=problem):
                reply = bridge.handle(frame(call(SQUEEZE, ident="t")))
            self.assertWire(reply, -32603, "t")
            self.assertEqual(set(reply), {"jsonrpc", "id", "error"})
            self.assertNotIn("boom", reply["error"]["message"])
        self.assertFalse(bridge.handle(frame(call(SQUEEZE)))["result"]["isError"])

    def test_gap_rob_12_bridge_error_receipts_carry_the_input_hash(self):
        for arguments in ({}, {"frames": []}, {**SQUEEZE, "extra": 1}, {"frames": [{"scale_permille": [1, 0, 1]}]}):
            result = ready().handle(frame(call(arguments)))["result"]
            receipt = result["structuredContent"]["receipt"]
            self.assertTrue(result["isError"])
            self.assertEqual((receipt["status"], receipt["result"]), ("error", None))
            self.assertEqual(receipt["input_sha256"], input_sha256(arguments))
            self.assertRegex(receipt["input_sha256"], r"\A[0-9a-f]{64}\Z")


if __name__ == "__main__":
    unittest.main()
