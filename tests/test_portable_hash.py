import hashlib
import tempfile
import unittest
from pathlib import Path
from src.data import portable_sha256


class PortableHashTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name: str, data: bytes) -> Path:
        path = self.dir/name
        path.write_bytes(data)
        return path

    def test_same_content_gives_same_hash_on_windows_and_mac(self):
        content = '[\n  {"lap_number": 1, "compound": "SOFT"}\n]'.encode('utf-8')
        mac = self.write('mac.json', content)
        windows = self.write('windows.json', content.replace(b'\n', b'\r\n'))
        self.assertNotEqual(mac.read_bytes(), windows.read_bytes())
        self.assertEqual(portable_sha256(mac), portable_sha256(windows))

    def test_lf_file_matches_classic_sha256(self):
        # En archivos con LF la huella portable coincide con sha256 clásico.
        content = b'a,b\n1,2\n'
        path = self.write('lf.csv', content)
        self.assertEqual(portable_sha256(path), hashlib.sha256(content).hexdigest())

    def test_real_content_change_is_still_detected(self):
        original = self.write('a.json', b'{"lap_duration": 92.608}\r\n')
        altered = self.write('b.json', b'{"lap_duration": 92.609}\r\n')
        self.assertNotEqual(portable_sha256(original), portable_sha256(altered))


if __name__ == '__main__':
    unittest.main()
