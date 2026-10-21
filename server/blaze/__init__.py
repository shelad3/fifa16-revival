"""
Blaze Protocol - Packet Structures

EA Blaze protocol uses 8-byte packet headers:
  - 2 bytes: packet type (command)
  - 1 byte:  component ID
  - 1 byte:  command ID within component
  - 2 bytes: error code
  - 2 bytes: payload length

Components in FIFA-era EA games:
  0x00 = Authentication
  0x01 = GameManager
  0x02 = UserSessions
  0x03 = Presence
  0x04 = Friends
  0x05 = Gameplay
  0x06 = Stats
  0x07 = Messaging
  0x08 = Gameroom
  0x09 = GameReporting
  0x0A = Util
  0x0B = Clubs
  0x0C = Channels
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class BlazeComponent(IntEnum):
    AUTHENTICATION = 0x00
    GAMEMANAGER = 0x01
    USER_SESSIONS = 0x02
    PRESENCE = 0x03
    FRIENDS = 0x04
    GAMEPLAY = 0x05
    STATS = 0x06
    MESSAGING = 0x07
    GAMEROOM = 0x08
    GAME_REPORTING = 0x09
    UTIL = 0x0A
    CLUBS = 0x0B
    CHANNELS = 0x0C


class PacketType(IntEnum):
    DATA = 0x00
    NOTIFICATION = 0x01


@dataclass
class BlazePacket:
    """Represents a single Blaze protocol packet."""
    packet_type: int = 0x00
    component: int = 0x00
    command: int = 0x00
    error_code: int = 0x0000
    message_id: int = 0x0000
    payload: bytes = b""

    @classmethod
    def from_bytes(cls, data: bytes) -> Optional["BlazePacket"]:
        if len(data) < 12:
            return None

        packet_type = int.from_bytes(data[0:2], "big")
        component = data[2]
        command = data[3]
        error_code = int.from_bytes(data[4:6], "big")
        message_id = int.from_bytes(data[6:8], "big")
        payload_len = int.from_bytes(data[8:12], "big")

        if len(data) < 12 + payload_len:
            return None

        payload = data[12:12 + payload_len]

        return cls(
            packet_type=packet_type,
            component=component,
            command=command,
            error_code=error_code,
            message_id=message_id,
            payload=payload
        )

    def to_bytes(self) -> bytes:
        header = (
            self.packet_type.to_bytes(2, "big") +
            bytes([self.component, self.command]) +
            self.error_code.to_bytes(2, "big") +
            self.message_id.to_bytes(2, "big") +
            len(self.payload).to_bytes(4, "big")
        )
        return header + self.payload

    def __repr__(self):
        comp_name = BlazeComponent(self.component).name if self.component in BlazeComponent else f"0x{self.component:02X}"
        return (f"BlazePacket(type={self.packet_type}, comp={comp_name}, "
                f"cmd=0x{self.command:02X}, err=0x{self.error_code:04X}, "
                f"msg_id={self.message_id}, payload_len={len(self.payload)})")


@dataclass
class TDFValue:
    """Represents a decoded TDF value."""
    name: str
    type: str
    value: object = None
    children: list = field(default_factory=list)

    def get(self, name: str, default=None):
        for child in self.children:
            if child.name == name:
                return child.value
        return default

    def get_child(self, name: str) -> Optional["TDFValue"]:
        for child in self.children:
            if child.name == name:
                return child
        return None

    def get_all(self, name: str) -> list:
        return [c for c in self.children if c.name == name]

    def __repr__(self):
        return f"TDF({self.name}={self.type}:{self.value!r})"


class TDFEncoder:
    """Encodes Python values into EA's Tag Data Format (TDF)."""

    @staticmethod
    def encode_string(name: str, value: str) -> bytes:
        encoded = value.encode("utf-8")
        return (
            TDFEncoder._encode_header(name, "STR") +
            len(encoded).to_bytes(2, "little") +
            encoded
        )

    @staticmethod
    def encode_int32(name: str, value: int) -> bytes:
        return TDFEncoder._encode_header(name, "I32") + value.to_bytes(4, "little", signed=True)

    @staticmethod
    def encode_uint32(name: str, value: int) -> bytes:
        return TDFEncoder._encode_header(name, "UI32") + value.to_bytes(4, "little")

    @staticmethod
    def encode_int64(name: str, value: int) -> bytes:
        return TDFEncoder._encode_header(name, "I64") + value.to_bytes(8, "little", signed=True)

    @staticmethod
    def encode_uint64(name: str, value: int) -> bytes:
        return TDFEncoder._encode_header(name, "UI64") + value.to_bytes(8, "little")

    @staticmethod
    def encode_bool(name: str, value: bool) -> bytes:
        return TDFEncoder._encode_header(name, "BOOL") + (b"\x01" if value else b"\x00")

    @staticmethod
    def encode_blob(name: str, data: bytes) -> bytes:
        return (
            TDFEncoder._encode_header(name, "BLOB") +
            len(data).to_bytes(2, "little") +
            data
        )

    @staticmethod
    def encode_struct(name: str, fields: bytes) -> bytes:
        return TDFEncoder._encode_header(name, "STRC") + fields

    @staticmethod
    def encode_list(name: str, element_type: str, elements: list) -> bytes:
        header = TDFEncoder._encode_header(name, "LIST")
        header += element_type.encode("ascii")[:4].ljust(4, b"\x00")
        header += len(elements).to_bytes(2, "little")
        return header + b"".join(elements)

    @staticmethod
    def encode_map(name: str, key_type: str, value_type: str, entries: list) -> bytes:
        header = TDFEncoder._encode_header(name, "MAP ")
        header += key_type.encode("ascii")[:4].ljust(4, b"\x00")
        header += value_type.encode("ascii")[:4].ljust(4, b"\x00")
        header += len(entries).to_bytes(2, "little")
        for key_data, val_data in entries:
            header += key_data + val_data
        return header

    @staticmethod
    def encode_pair(name: str, first: bytes, second: bytes) -> bytes:
        return TDFEncoder._encode_header(name, "PAIR") + first + second

    @staticmethod
    def _encode_header(name: str, type_code: str) -> bytes:
        name_bytes = name.encode("ascii")[:3].ljust(3, b"\x00")
        type_bytes = type_code.encode("ascii")[:4].ljust(4, b"\x00")
        return name_bytes + type_bytes


class TDFDecoder:
    """Decodes EA's Tag Data Format into Python structures."""

    @staticmethod
    def decode(data: bytes) -> list:
        values = []
        pos = 0
        while pos < len(data):
            try:
                value, pos = TDFDecoder._decode_value(data, pos)
                values.append(value)
            except (IndexError, struct.error):
                break
        return values

    @staticmethod
    def _decode_value(data: bytes, pos: int) -> tuple:
        name = data[pos:pos+3].decode("ascii", errors="replace").rstrip("\x00")
        type_code = data[pos+3:pos+7].decode("ascii", errors="replace").rstrip("\x00")
        pos += 7

        if type_code == "STR":
            str_len = int.from_bytes(data[pos:pos+2], "little")
            pos += 2
            value = data[pos:pos+str_len].decode("utf-8", errors="replace")
            pos += str_len
            return TDFValue(name, "STR", value), pos

        elif type_code == "I32":
            value = int.from_bytes(data[pos:pos+4], "little", signed=True)
            return TDFValue(name, "I32", value), pos + 4

        elif type_code == "UI32":
            value = int.from_bytes(data[pos:pos+4], "little")
            return TDFValue(name, "UI32", value), pos + 4

        elif type_code == "I64":
            value = int.from_bytes(data[pos:pos+8], "little", signed=True)
            return TDFValue(name, "I64", value), pos + 8

        elif type_code == "UI64":
            value = int.from_bytes(data[pos:pos+8], "little")
            return TDFValue(name, "UI64", value), pos + 8

        elif type_code == "BOOL":
            value = data[pos] != 0
            return TDFValue(name, "BOOL", value), pos + 1

        elif type_code == "BLOB":
            blob_len = int.from_bytes(data[pos:pos+2], "little")
            pos += 2
            value = data[pos:pos+blob_len]
            return TDFValue(name, "BLOB", value), pos + blob_len

        elif type_code == "STRC":
            end_marker = TDFDecoder._find_struct_end(data, pos)
            children = TDFDecoder._decode_typed_range(data, pos, end_marker)
            result = TDFValue(name, "STRC", None, children)
            return result, end_marker

        elif type_code == "LIST":
            elem_type = data[pos:pos+4].decode("ascii", errors="replace").rstrip("\x00")
            pos += 4
            count = int.from_bytes(data[pos:pos+2], "little")
            pos += 2
            children = []
            for _ in range(count):
                child, pos = TDFDecoder._decode_typed_element(data, pos, elem_type)
                children.append(child)
            return TDFValue(name, "LIST", None, children), pos

        elif type_code == "MAP ":
            key_type = data[pos:pos+4].decode("ascii", errors="replace").rstrip("\x00")
            pos += 4
            val_type = data[pos:pos+4].decode("ascii", errors="replace").rstrip("\x00")
            pos += 4
            count = int.from_bytes(data[pos:pos+2], "little")
            pos += 2
            children = []
            for _ in range(count):
                key_child, pos = TDFDecoder._decode_typed_element(data, pos, key_type)
                val_child, pos = TDFDecoder._decode_typed_element(data, pos, val_type)
                children.append(key_child)
                children.append(val_child)
            return TDFValue(name, "MAP", None, children), pos

        elif type_code == "PAIR":
            first, pos = TDFDecoder._decode_value(data, pos)
            second, pos = TDFDecoder._decode_value(data, pos)
            return TDFValue(name, "PAIR", None, [first, second]), pos

        else:
            raise ValueError(f"Unknown TDF type: {type_code!r} at pos {pos}")

    @staticmethod
    def _decode_typed_element(data: bytes, pos: int, type_code: str) -> tuple:
        if type_code == "STR":
            str_len = int.from_bytes(data[pos:pos+2], "little")
            pos += 2
            value = data[pos:pos+str_len].decode("utf-8", errors="replace")
            return TDFValue("", "STR", value), pos + str_len
        elif type_code == "I32":
            return TDFValue("", "I32", int.from_bytes(data[pos:pos+4], "little", signed=True)), pos + 4
        elif type_code == "UI32":
            return TDFValue("", "UI32", int.from_bytes(data[pos:pos+4], "little")), pos + 4
        elif type_code == "I64":
            return TDFValue("", "I64", int.from_bytes(data[pos:pos+8], "little", signed=True)), pos + 8
        elif type_code == "UI64":
            return TDFValue("", "UI64", int.from_bytes(data[pos:pos+8], "little")), pos + 8
        elif type_code == "BOOL":
            return TDFValue("", "BOOL", data[pos] != 0), pos + 1
        elif type_code == "BLOB":
            blob_len = int.from_bytes(data[pos:pos+2], "little")
            pos += 2
            return TDFValue("", "BLOB", data[pos:pos+blob_len]), pos + blob_len
        elif type_code == "STRC":
            end_marker = TDFDecoder._find_struct_end(data, pos)
            children = TDFDecoder._decode_typed_range(data, pos, end_marker)
            return TDFValue("", "STRC", None, children), end_marker
        else:
            raise ValueError(f"Unknown list element type: {type_code!r}")

    @staticmethod
    def _decode_typed_range(data: bytes, start: int, end: int) -> list:
        children = []
        pos = start
        while pos < end:
            try:
                child, pos = TDFDecoder._decode_value(data, pos)
                children.append(child)
            except Exception:
                break
        return children

    @staticmethod
    def _find_struct_end(data: bytes, start: int) -> int:
        depth = 1
        pos = start
        while pos < len(data) - 7:
            type_code = data[pos+3:pos+7].decode("ascii", errors="replace").rstrip("\x00")
            if type_code == "STRC":
                depth += 1
                pos = TDFDecoder._find_struct_end(data, pos + 7) + 7
            elif type_code == "STR":
                str_len = int.from_bytes(data[pos+7:pos+9], "little")
                pos += 9 + str_len
            elif type_code == "I32" or type_code == "UI32":
                pos += 11
            elif type_code == "I64" or type_code == "UI64":
                pos += 15
            elif type_code == "BOOL":
                pos += 8
            elif type_code == "BLOB":
                blob_len = int.from_bytes(data[pos+7:pos+9], "little")
                pos += 9 + blob_len
            else:
                pos += 1
        return pos


import struct
