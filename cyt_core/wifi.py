"""Minimal passive 802.11 header decoder. No payload retention or identity linking."""
import struct


class SkipFrame(ValueError):
    """A counted reason a captured frame cannot produce an observation."""


def unwrap(packet, dlt):
    if not isinstance(packet, bytes) or not packet:
        raise SkipFrame("missing_packet_bytes")
    if dlt == 105:
        return packet
    if dlt != 127:
        raise SkipFrame("unsupported_dlt")
    if len(packet) < 8 or packet[0] != 0:
        raise SkipFrame("invalid_radiotap")
    length, present = struct.unpack_from("<HI", packet, 2)
    if not 8 <= length <= len(packet):
        raise SkipFrame("invalid_radiotap")
    offset, mask = 8, present
    while mask & (1 << 31):
        if offset + 4 > length:
            raise SkipFrame("invalid_radiotap")
        mask = struct.unpack_from("<I", packet, offset)[0]
        offset += 4
    if present & 1:  # TSFT precedes flags, aligned to eight bytes.
        offset = (offset + 7) // 8 * 8 + 8
    if offset > length:
        raise SkipFrame("invalid_radiotap")
    flags = 0
    if present & 2:
        if offset >= length:
            raise SkipFrame("invalid_radiotap")
        flags = packet[offset]
    if flags & 0x40:
        raise SkipFrame("bad_fcs")
    frame = packet[length:]
    if flags & 0x10:
        if len(frame) < 4:
            raise SkipFrame("truncated_frame")
        frame = frame[:-4]
    return frame


def decode(packet, dlt):
    frame = unwrap(packet, dlt)
    if len(frame) < 2:
        raise SkipFrame("truncated_frame")
    control = int.from_bytes(frame[:2], "little")
    if control & 3:
        raise SkipFrame("unsupported_frame_version")
    frame_type, subtype = (control >> 2) & 3, (control >> 4) & 15
    if frame_type not in (0, 2) or (frame_type == 0 and subtype not in (4, 8)):
        raise SkipFrame("unsupported_frame_type")
    if len(frame) < 24:
        raise SkipFrame("truncated_frame")
    # Address 2 is the over-the-air transmitter, including ToDS/FromDS data.
    transmitter = frame[10:16]
    if transmitter[0] & 1 or not any(transmitter):
        raise SkipFrame("invalid_transmitter")
    result = {"address": ":".join(f"{b:02X}" for b in transmitter)}
    if frame_type == 2:
        required = 24 + (6 if control & 0x0300 == 0x0300 else 0)
        if subtype & 8:
            required += 2  # QoS control
            if control & 0x8000:
                required += 4  # HT control
        if len(frame) < required:
            raise SkipFrame("truncated_frame")
        return dict(result, kind="data_header")
    if control & 0xC700 or int.from_bytes(frame[22:24], "little") & 15:
        raise SkipFrame("unsupported_management_flags")
    offset = 24 + (12 if subtype == 8 else 0)
    if len(frame) < offset:
        raise SkipFrame("truncated_frame")
    ssid = None
    while offset < len(frame):
        if offset + 2 > len(frame):
            raise SkipFrame("truncated_information_element")
        tag, size = frame[offset:offset + 2]
        offset += 2
        if offset + size > len(frame):
            raise SkipFrame("truncated_information_element")
        if tag == 0:
            if ssid is not None or size > 32:
                raise SkipFrame("invalid_ssid_element")
            ssid = frame[offset:offset + size]
        offset += size
    if ssid is None:
        raise SkipFrame("missing_ssid_element")
    try:
        decoded = ssid.decode("utf-8")
    except UnicodeDecodeError:
        decoded = None
    return dict(result, kind="probe" if subtype == 4 else "beacon", ssid=decoded, ssid_hex=ssid.hex())
