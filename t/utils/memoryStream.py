import struct

# 设定一个内存分配的安全上限 (例如 2GB)，防止读取错误数据导致崩溃
MAX_ALLOC_LIMIT = 2 * 1024 * 1024 * 1024 

class MemoryStream:
    def __init__(self, Data=b"", IOMode = "read"):
        self.Location = 0
        self.Data = bytearray(Data)
        if IOMode == "read":
            self.reading = True
        else:
            self.reading = False

    def open(self, Data, IOMode = "read"): # Open Stream
        self.Data = bytearray(Data)
        if IOMode == "read":
            self.reading = True
        else:
            self.reading = False

    def SetReadMode(self):
        self.reading = True

    def SetWriteMode(self):
        self.reading = False

    def IsReading(self):
        return self.reading

    def IsWriting(self):
        return not self.reading

    def seek(self, Location): # Go To Position In Stream
        # --- 安全检查开始 ---
        if Location < 0:
            raise Exception(f"MemoryStream Error: Attempted to seek to negative location: {Location}")
        
        # 如果跳转位置极其巨大，说明读取到了错误的 Offset 数据
        if Location > MAX_ALLOC_LIMIT or Location > len(self.Data) * 10: 
             raise Exception(f"MemoryStream Safety Trigger: Code attempted to seek to {Location}, which is suspiciously large. Likely file format mismatch.")
        # --- 安全检查结束 ---

        self.Location = Location
        if self.Location > len(self.Data):
            missing_bytes = self.Location - len(self.Data)
            
            # --- 再次检查分配大小 ---
            if missing_bytes > MAX_ALLOC_LIMIT:
                 raise Exception(f"MemoryStream Crash Prevented: Attempted to allocate {missing_bytes} bytes. The file header parsing is likely misaligned.")
            # -----------------------
            
            self.Data.extend(bytearray(missing_bytes))

    def tell(self): # Get Position In Stream
        return self.Location

    def read(self, length=-1): # Read Bytes From Stream
        if length == -1:
            length = len(self.Data) - self.Location
            
        # --- 安全检查 ---
        if length > MAX_ALLOC_LIMIT:
            raise Exception(f"MemoryStream Safety Trigger: Attempted to read {length} bytes. This value is likely garbage data interpreted as a size.")
        # ---------------

        if self.Location + length > len(self.Data):
            raise Exception(f"reading past end of stream. Loc:{self.Location} Len:{length} StreamSize:{len(self.Data)}")

        newData = self.Data[self.Location:self.Location+length]
        self.Location += length
        return bytes(newData)

    def write(self, bytes_data): # Write Bytes To Stream
        # Rename bytes argument to bytes_data to avoid shadowing built-in bytes()
        length = len(bytes_data)
        
        required_len = self.Location + length
        if required_len > len(self.Data):
             # 自动扩展流大小以适应写入
             missing = required_len - len(self.Data)
             if missing > MAX_ALLOC_LIMIT:
                 raise Exception(f"MemoryStream Safety: Attempted to write excessively past stream end. Missing: {missing}")
             self.Data.extend(bytearray(missing))

        self.Data[self.Location:self.Location+length] = bytes_data
        self.Location += length

    def serialize(self, value, format, size):
        if self.reading:
            return struct.unpack(format, self.read(size))[0]
        else:
            self.write(struct.pack(format, value))
            return value

    def int8(self, value):
        return self.serialize(value, '<b', 1)

    def uint8(self, value):
        return self.serialize(value, '<B', 1)

    def int16(self, value):
        return self.serialize(value, '<h', 2)

    def uint16(self, value):
        return self.serialize(value, '<H', 2)

    def int32(self, value):
        return self.serialize(value, '<i', 4)

    def uint32(self, value):
        return self.serialize(value, '<I', 4)

    def int64(self, value):
        return self.serialize(value, '<q', 8)

    def uint64(self, value):
        return self.serialize(value, '<Q', 8)

    def float16(self, value):
        return self.serialize(value, '<e', 2)

    def float32(self, value):
        return self.serialize(value, '<f', 4)

    def float64(self, value):
        return self.serialize(value, '<d', 8)

    def __resize_vec(self, value, length):
        value = list(value)
        if len(value) < length:
            dif = length - len(value)
            value.extend([0]*dif)
        if len(value) > length:
            value = value[:length]
        return value

    def vec2_float(self, value):
        if len(value) != 2:
            value = self.__resize_vec(value, 2)
        return [self.float32(value[0]), self.float32(value[1])]

    def vec3_float(self, value):
        if len(value) != 3:
            value = self.__resize_vec(value, 3)
        return [self.float32(value[0]), self.float32(value[1]), self.float32(value[2])]

    def vec2_half(self, value):
        if len(value) != 2:
            value = self.__resize_vec(value, 2)
        return [self.float16(value[0]), self.float16(value[1])]

    def vec3_half(self, value):
        if len(value) != 3:
            value = self.__resize_vec(value, 3)
        return [self.float16(value[0]), self.float16(value[1]), self.float16(value[2])]

    def vec4_half(self, value):
        if len(value) != 4:
            value = self.__resize_vec(value, 4)
        return [self.float16(value[0]), self.float16(value[1]), self.float16(value[2]), self.float16(value[3])]

    def vec4_uint8(self, value):
        if len(value) != 4:
            value = self.__resize_vec(value, 4)
        return [self.uint8(value[0]), self.uint8(value[1]), self.uint8(value[2]), self.uint8(value[3])]

    def vec4_uint16(self, value):
        if len(value) != 4:
            value = self.__resize_vec(value, 4)
        return [self.uint16(value[0]), self.uint16(value[1]), self.uint16(value[2]), self.uint16(value[3])]

    def vec4_uint32(self, value):
        if len(value) != 4:
            value = self.__resize_vec(value, 4)
        return [self.uint32(value[0]), self.uint32(value[1]), self.uint32(value[2]), self.uint32(value[3])]

    def array(self, type, value, size = -1):
        if size == -1:
            size = len(value)
        if len(value) != size:
            value = range(size)

        for n in range(size):
            value[n] = type()
        return value

    def bytes(self, value, size = -1):
        if size == -1:
            size = len(value)
        if len(value) != size:
            value = bytearray(size)

        if self.reading:
            return bytearray(self.read(size))
        else:
            self.write(value)
            return bytearray(value)

def InsureBitLength(bits, length):
    # cut off if to big
    if len(bits) > length:
        bits = bits[:length]
    # add to start if to small
    newbits = str().ljust(length-len(bits),"0")
    return newbits + bits

def TenBitSigned(U32):
    X = (U32 & 1023)
    Y = ((U32 >> 10) & 1023)
    Z = ((U32 >> 20) & 1023)
    W = (U32 >> 30)
    v = [((X - 511) / 512), ((Y - 511) / 512), ((Z - 511) / 512), W / 3]
    return v

def TenBitUnsigned(U32):
    X = (U32 & 1023)
    Y = ((U32 >> 10) & 1023)
    Z = ((U32 >> 20) & 1023)
    W = (U32 >> 30)
    v = [(X / 1023), (Y  / 1023), (Z  / 1023), W / 3]
    return v

def MakeTenBitUnsigned(vec):
    x = vec[0];y = vec[1];z = vec[2]
    x *= 1024; y *= 1024; z *= 1024
    xbin = bin(int(x))[2:]; ybin = bin(int(y))[2:]; zbin = bin(int(z))[2:]
    xbin = InsureBitLength(xbin, 10); ybin = InsureBitLength(ybin, 10); zbin = InsureBitLength(zbin, 10);
    binary = InsureBitLength(zbin+ybin+xbin, 32)
    return int(binary, 2)

def MakeTenBitSigned(vec):
    x = vec[0];y = vec[1];z = vec[2]
    x = (abs(x)*512); y =(abs(y)*512); z =(abs(z)*512)
    # add bias
    if vec[0] < 0:
        x = abs(x-511)
    else:
        x += 511
    if vec[1] < 0:
        y = abs(y-511)
    else:
        y += 511
    if vec[2] < 0:
        z = abs(z-511)
    else:
        z += 511
    xbin = bin(int(x))[2:]; ybin = bin(int(y))[2:]; zbin = bin(int(z))[2:]
    xbin = InsureBitLength(xbin, 10); ybin = InsureBitLength(ybin, 10); zbin = InsureBitLength(zbin, 10);
    binary = InsureBitLength(zbin+ybin+xbin, 32)
    return int(binary, 2)
