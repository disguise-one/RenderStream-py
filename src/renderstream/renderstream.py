import ctypes
import ctypes.wintypes
import winreg
import sys
import os
import os.path
from typing import Callable
from .ctypes_helpers import AnnotatedStructure, AnnotatedUnion, Enumeration

logger_t = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
StreamHandle = ctypes.c_uint64
CameraHandle = ctypes.c_uint64

pID3D11Device = ctypes.c_void_p
pID3D11Resource = ctypes.c_void_p

pID3D12Device = ctypes.c_void_p
pID3D12CommandQueue = ctypes.c_void_p
pID3D12Resource = ctypes.c_void_p


class VkDevice_T(ctypes.Structure):
    pass


VkDevice = ctypes.POINTER(VkDevice_T)


class VkDeviceMemory_T(ctypes.Structure):
    pass


VkDeviceMemory = ctypes.POINTER(VkDeviceMemory_T)

VkDeviceSize = ctypes.c_uint64


class VkSemaphore_T(ctypes.Structure):
    pass


VkSemaphore = ctypes.POINTER(VkSemaphore_T)

VERSION_MAJOR = 1
VERSION_MINOR = 31


class RS_ERROR(Enumeration):
    SUCCESS = 0
    INITIALISED = 1
    ALREADY_INITIALISED = 2
    INVALID_HANDLE = 3
    MAX_SENDERS_REACHED = 4
    BAD_STREAM_TYPE = 5
    NOT_FOUND = 6
    INCORRECT_SCHEMA = 7
    INVALID_PARAMETERS = 8
    BUFFER_OVERFLOW = 9
    TIMEOUT = 10
    STREAMS_CHANGED = 11
    INCOMPATIBLE_VERSION = 12
    FAILED_TO_GET_DXDEVICE_FROM_RESOURCE = 13
    FAILED_TO_INITIALISE_GPGPU = 14
    QUIT = 15
    UNSPECIFIED = 16


class RemoteParameterType(Enumeration):
    NUMBER = 0
    IMAGE = 1
    POSE = 2  # 4x4 TR matrix
    TRANSFORM = 3  # 4x4 TRS matrix
    TEXT = 4


class RemoteParameterDmxType(Enumeration):
    DEFAULT = 0
    _8 = 1
    _16_BE = 2


class UseDX12SharedHeapFlag(Enumeration):
    USE_SHARED_HEAP_FLAG = 0
    DO_NOT_USE_SHARED_HEAP_FLAG = 1


class RSPixelFormat(Enumeration):
    INVALID = 0
    BGRA8 = 1
    BGRX8 = 2
    RGBA32F = 3
    RGBA16 = 4
    RGBA8 = 5
    RGBX8 = 6


class SenderFrameType(Enumeration):
    HOST_MEMORY = 0
    DX11_TEXTURE = 1
    DX12_TEXTURE = 2
    OPENGL_TEXTURE = 3
    VULKAN_TEXTURE = 4
    UNKNOWN = 5


class FrameDataFlags(Enumeration):
    FRAMEDATA_NO_FLAGS = 0
    FRAMEDATA_RESET = 1


class RemoteParameterFlags(Enumeration):
    NO_FLAGS = 0
    NO_SEQUENCE = 1
    READ_ONLY = 2


class NumericalDefaults(AnnotatedStructure):
    _pack_ = 4
    min: ctypes.c_float
    max: ctypes.c_float
    step: ctypes.c_float
    defaultValue: ctypes.c_float

    def __init__(self, default: float, min: float, max: float, step: float):
        self.defaultValue = default
        self.min = min
        self.max = max
        self.step = step


class TextDefaults(AnnotatedStructure):
    _pack_ = 4
    defaultValue: ctypes.c_char_p

    def __init__(self, default: str):
        self.defaultValue = bytes(default, encoding="utf-8")


class RemoteParameterTypeDefaults(AnnotatedUnion):
    _pack_ = 4
    number: NumericalDefaults
    text: TextDefaults

    def __init__(self, value: NumericalDefaults | TextDefaults):
        if isinstance(value, NumericalDefaults):
            self.number = value
        else:
            self.text = value


class RemoteParameter(AnnotatedStructure):
    _pack_ = 4
    group: ctypes.c_char_p
    displayName: ctypes.c_char_p
    key: ctypes.c_char_p
    type: RemoteParameterType
    defaults: RemoteParameterTypeDefaults
    nOptions: ctypes.c_uint32
    options: ctypes.POINTER(ctypes.c_char_p)

    dmxOffset: ctypes.c_int32
    dmxType: RemoteParameterDmxType
    flags: ctypes.c_uint32

    def __init__(
        self,
        key: str,
        displayName: str,
        group: str,
        defaults: NumericalDefaults | TextDefaults,
        options: list[str] = [],
        dmxOffset: int = 0,
        dmxType: RemoteParameterDmxType = RemoteParameterDmxType.DEFAULT,
        flags: RemoteParameterFlags = RemoteParameterFlags.NO_FLAGS,
    ):
        self.group = bytes(group, encoding="utf-8")
        self.displayName = bytes(displayName, encoding="utf-8")
        self.key = bytes(key, encoding="utf-8")
        self.type = RemoteParameterType.NUMBER if isinstance(defaults, NumericalDefaults) else RemoteParameterType.TEXT
        self.defaults = RemoteParameterTypeDefaults(defaults)

        self.nOptions = len(options)
        self.options = (ctypes.c_char_p * len(options))(*(bytes(option, encoding="utf-8") for option in options))

        self.dmxOffset = dmxOffset
        self.dmxType = dmxType

        self.flags = flags


class RemoteParameters(AnnotatedStructure):
    _pack_ = 4
    name: ctypes.c_char_p
    nParameters: ctypes.c_uint32
    parameters: ctypes.POINTER(RemoteParameter)
    hash: ctypes.c_uint64

    def __init__(self, name: str, parameters: list[RemoteParameter]):
        self.name = bytes(name, encoding="utf-8")
        self.nParameters = len(parameters)
        self.parameters = (RemoteParameter * len(parameters))(*parameters)


class Scenes(AnnotatedStructure):
    _pack_ = 4
    nScenes: ctypes.c_uint32
    scenes: ctypes.POINTER(RemoteParameters)


class Channels(AnnotatedStructure):
    _pack_ = 4
    nChannels: ctypes.c_uint32
    channels: ctypes.POINTER(ctypes.c_char_p)


class Schema(AnnotatedStructure):
    _pack_ = 4
    engineName: ctypes.c_char_p
    engineVersion: ctypes.c_char_p
    info: ctypes.c_char_p
    channels: Channels
    scenes: Scenes

    def __init__(
        self,
        channels: list[str],
        scenes: list[RemoteParameters],
        engineName: str = "",
        engineVersion: str = "",
        info: str = "",
    ):
        self.engineName = bytes(engineName, encoding="utf-8")
        self.engineVersion = bytes(engineVersion, encoding="utf-8")
        self.info = bytes(info, encoding="utf-8")

        self.channels.nChannels = len(channels)
        self.channels.channels = (ctypes.c_char_p * len(channels))(
            *(bytes(chan, encoding="utf-8") for chan in channels)
        )

        self.scenes.nScenes = len(scenes)
        self.scenes.scenes = (RemoteParameters * len(scenes))(*scenes)


pSchema = ctypes.POINTER(Schema)


class ImageFrameData(AnnotatedStructure):
    _pack_ = 4
    width: ctypes.c_uint32
    height: ctypes.c_uint32
    format: RSPixelFormat
    imageId: ctypes.c_int64


class ProjectionClipping(AnnotatedStructure):
    """Normalised (0-1) clipping planes for the edges of the camera frustum, to be used to perform off-axis
    perspective projection, or to offset and scale 2D orthographic matrices."""

    _pack_ = 4
    left: ctypes.c_float
    right: ctypes.c_float
    top: ctypes.c_float
    bottom: ctypes.c_float


class StreamDescription(AnnotatedStructure):
    _pack_ = 4
    handle: StreamHandle
    channel: ctypes.c_char_p
    mappingId: ctypes.c_uint64
    iViewpoint: ctypes.c_int32
    name: ctypes.c_char_p
    width: ctypes.c_uint32
    height: ctypes.c_uint32
    format: RSPixelFormat
    clipping: ProjectionClipping


class StreamDescriptions(AnnotatedStructure):
    _pack_ = 4
    nStreams: ctypes.c_uint32
    streams: ctypes.POINTER(StreamDescription)


pStreamDescriptions = ctypes.POINTER(StreamDescriptions)


class D3TrackingData(AnnotatedStructure):
    "Tracking data required by d3 but not used to render content"
    _pack_ = 4
    virtualZoomScale: ctypes.c_float
    virtualReprojectionRequired: ctypes.c_uint8
    xRealCamera: ctypes.c_float
    yRealCamera: ctypes.c_float
    zRealCamera: ctypes.c_float
    rxRealCamera: ctypes.c_float
    ryRealCamera: ctypes.c_float
    rzRealCamera: ctypes.c_float


class CameraData(AnnotatedStructure):
    _pack_ = 4
    id: StreamHandle
    cameraHandle: CameraHandle
    x: ctypes.c_float
    y: ctypes.c_float
    z: ctypes.c_float
    rx: ctypes.c_float
    ry: ctypes.c_float
    rz: ctypes.c_float
    focalLength: ctypes.c_float
    sensorX: ctypes.c_float
    sensorY: ctypes.c_float
    cx: ctypes.c_float
    cy: ctypes.c_float
    nearZ: ctypes.c_float
    farZ: ctypes.c_float
    orthoWidth: ctypes.c_float  # If > 0, an orthographic camera should be used
    d3Tracking: D3TrackingData


class FrameData(AnnotatedStructure):
    _pack_ = 4
    tTracked: ctypes.c_double
    localTime: ctypes.c_double
    localTimeDelta: ctypes.c_double
    frameRateNumerator: ctypes.c_uint
    frameRateDenominator: ctypes.c_uint
    flags: FrameDataFlags
    scene: ctypes.c_uint32


class CameraResponseData(AnnotatedStructure):
    _pack_ = 4
    tTracked: ctypes.c_double
    camera: CameraData


class FrameResponseData(AnnotatedStructure):
    _pack_ = 16
    cameraData: ctypes.POINTER(CameraResponseData)
    schemaHash: ctypes.c_uint64
    parameterDataSize: ctypes.c_uint32
    parameterData: ctypes.c_void_p
    textDataCount: ctypes.c_uint32
    textData: ctypes.POINTER(ctypes.c_char_p)

    def __init__(self, cameraData: CameraResponseData, scene: RemoteParameters, outputParams: dict[str, float | str]):
        self.cameraData = ctypes.pointer(cameraData)
        self.schemaHash = scene.hash

        floats: list[float] = []
        texts: list[str] = []

        # Build the flattened list in the same order as the parameters were published
        for iParam in range(scene.nParameters):
            param: RemoteParameter = scene.parameters[iParam]
            if not param.flags & RemoteParameterFlags.READ_ONLY.value:
                continue

            key = str(param.key, encoding="utf-8")
            value = outputParams[key]  # if this isn't present, the schema isn't matched with the outputParams somehow
            if param.type == RemoteParameterType.NUMBER:
                if not isinstance(value, float):
                    raise ValueError(f"Value for {key} should be float")
                floats.append(value)
            elif param.type == RemoteParameterType.TEXT:
                if not isinstance(value, str):
                    raise ValueError(f"Value for {key} should be str")
                texts.append(value)
            else:
                raise ValueError(f"Unexpected {value!r} in output params")

        fParams = (ctypes.c_float * len(floats))(*floats)
        self.parameterData = ctypes.cast(fParams, ctypes.c_void_p)
        self.parameterDataSize = ctypes.sizeof(fParams)

        self.textDataCount = len(texts)
        self.textData = (ctypes.c_char_p * len(texts))(*texts)


class HostMemoryData(AnnotatedStructure):
    _pack_ = 4
    data: ctypes.POINTER(ctypes.c_uint8)
    stride: ctypes.c_uint32
    format: RSPixelFormat


class Dx11Data(AnnotatedStructure):
    _pack_ = 4
    resource: pID3D11Resource


class Dx12Data(AnnotatedStructure):
    _pack_ = 4
    resource: pID3D12Resource


class OpenGlData(AnnotatedStructure):
    _pack_ = 4
    texture: ctypes.c_uint


class VulkanData(AnnotatedStructure):
    _pack_ = 4
    memory: VkDeviceMemory
    size: VkDeviceSize
    format: RSPixelFormat
    width: ctypes.c_uint32
    height: ctypes.c_uint32
    waitSemaphore: VkSemaphore
    waitSemaphoreValue: ctypes.c_uint64
    signalSemaphore: VkSemaphore
    signalSemaphoreValue: ctypes.c_uint64


class SenderFrameTypeData(AnnotatedUnion):
    _pack_ = 4
    cpu: HostMemoryData
    dx11: Dx11Data
    dx12: Dx12Data
    gl: OpenGlData
    vk: VulkanData


class SenderFrame(AnnotatedStructure):
    _pack_ = 4
    type: SenderFrameType
    data: SenderFrameTypeData

    def __init__(self, data: HostMemoryData | Dx11Data | Dx12Data | OpenGlData | VulkanData):
        if isinstance(data, HostMemoryData):
            self.type = SenderFrameType.HOST_MEMORY
            self.data.cpu = data
        elif isinstance(data, Dx11Data):
            self.type = SenderFrameType.DX11_TEXTURE
            self.data.dx11 = data
        elif isinstance(data, Dx12Data):
            self.type = SenderFrameType.DX12_TEXTURE
            self.data.dx12 = data
        elif isinstance(data, OpenGlData):
            self.type = SenderFrameType.OPENGL_TEXTURE
            self.data.gl = data
        elif isinstance(data, VulkanData):
            self.type = SenderFrameType.VULKAN_TEXTURE
            self.data.vk = data
        else:
            raise TypeError(f"Unexpected parameter of type '{type(data).__name__}'")


class ProfilingEntry(AnnotatedStructure):
    _pack_ = 4
    name: ctypes.c_char_p
    value: ctypes.c_float


class RenderStreamError(Exception):
    def __init__(self, error):
        self.error = error


def checkRsErrorOK(value):
    if value != RS_ERROR.SUCCESS.value:
        raise RenderStreamError(RS_ERROR(value))
    return RS_ERROR.SUCCESS


def loadRenderStreamFromRegistry():
    suiteKey = winreg.OpenKeyEx(
        winreg.HKEY_CURRENT_USER, "Software\\d3 Technologies\\d3 Production Suite", 0, winreg.KEY_READ
    )

    exePath, exePathType = winreg.QueryValueEx(suiteKey, "exe path")
    assert exePathType == winreg.REG_SZ

    exeDir = os.path.dirname(exePath)
    renderStreamDllPath = os.path.join(exeDir, "d3renderstream.dll")

    print("Loading RenderStream from '%s'" % renderStreamDllPath)
    if not os.path.exists(renderStreamDllPath):
        raise EnvironmentError("Disguise install is missing from '%s'" % exeDir)

    # TODO: When using Python > 3.8, we can use winmode=0x00000100 in the CDLL ctor, and no need to
    # modify the environment
    os.environ["PATH"] = os.environ["PATH"] + os.pathsep + exeDir
    renderStreamDll = ctypes.CDLL(renderStreamDllPath)

    renderStreamDll.rs_registerLoggingFunc.argtypes = [logger_t]
    renderStreamDll.rs_registerLoggingFunc.restype = None
    renderStreamDll.rs_registerErrorLoggingFunc.argtypes = [logger_t]
    renderStreamDll.rs_registerErrorLoggingFunc.restype = None
    renderStreamDll.rs_registerVerboseLoggingFunc.argtypes = [logger_t]
    renderStreamDll.rs_registerVerboseLoggingFunc.restype = None
    renderStreamDll.rs_unregisterLoggingFunc.argtypes = []
    renderStreamDll.rs_unregisterLoggingFunc.restype = None
    renderStreamDll.rs_unregisterErrorLoggingFunc.argtypes = []
    renderStreamDll.rs_unregisterErrorLoggingFunc.restype = None
    renderStreamDll.rs_unregisterVerboseLoggingFunc.argtypes = []
    renderStreamDll.rs_unregisterVerboseLoggingFunc.restype = None

    renderStreamDll.rs_initialise.argtypes = [ctypes.c_int, ctypes.c_int]
    renderStreamDll.rs_initialise.restype = checkRsErrorOK

    renderStreamDll.rs_initialise.argtypes = [ctypes.c_int, ctypes.c_int]
    renderStreamDll.rs_initialise.restype = checkRsErrorOK

    renderStreamDll.rs_initialiseGpGpuWithoutInterop.argtypes = [pID3D11Device]
    renderStreamDll.rs_initialiseGpGpuWithoutInterop.restype = checkRsErrorOK
    renderStreamDll.rs_initialiseGpGpuWithDX11Device.argtypes = [pID3D11Device]
    renderStreamDll.rs_initialiseGpGpuWithDX11Device.restype = checkRsErrorOK
    renderStreamDll.rs_initialiseGpGpuWithDX11Resource.argtypes = [pID3D11Resource]
    renderStreamDll.rs_initialiseGpGpuWithDX11Resource.restype = checkRsErrorOK
    renderStreamDll.rs_initialiseGpGpuWithDX12DeviceAndQueue.argtypes = [pID3D12Device, pID3D12CommandQueue]
    renderStreamDll.rs_initialiseGpGpuWithDX12DeviceAndQueue.restype = checkRsErrorOK
    renderStreamDll.rs_initialiseGpGpuWithOpenGlContexts.argtypes = [ctypes.c_void_p, ctypes.c_void_p]  # [HGLRC, HDC]
    renderStreamDll.rs_initialiseGpGpuWithOpenGlContexts.restype = checkRsErrorOK
    renderStreamDll.rs_initialiseGpGpuWithVulkanDevice.argtypes = [VkDevice]
    renderStreamDll.rs_initialiseGpGpuWithVulkanDevice.restype = checkRsErrorOK

    renderStreamDll.rs_shutdown.argtypes = []
    renderStreamDll.rs_shutdown.restype = checkRsErrorOK

    # non-isolated functions, these require init prior to use
    renderStreamDll.rs_useDX12SharedHeapFlag.argtypes = [ctypes.POINTER(UseDX12SharedHeapFlag)]
    renderStreamDll.rs_useDX12SharedHeapFlag.restype = checkRsErrorOK

    renderStreamDll.rs_saveSchema.argtypes = [ctypes.c_char_p, ctypes.POINTER(Schema)]
    renderStreamDll.rs_saveSchema.restype = checkRsErrorOK

    renderStreamDll.rs_loadSchema.argtypes = [ctypes.c_char_p, ctypes.POINTER(Schema), ctypes.POINTER(ctypes.c_uint32)]
    renderStreamDll.rs_loadSchema.restype = checkRsErrorOK

    # workload functions, these require the process to be running inside d3's asset launcher environment
    renderStreamDll.rs_setSchema.argtypes = [ctypes.POINTER(Schema)]
    renderStreamDll.rs_setSchema.restype = checkRsErrorOK

    renderStreamDll.rs_getStreams.argtypes = [ctypes.POINTER(StreamDescriptions), ctypes.POINTER(ctypes.c_uint32)]
    renderStreamDll.rs_getStreams.restype = checkRsErrorOK

    renderStreamDll.rs_awaitFrameData.argtypes = [ctypes.c_int, ctypes.POINTER(FrameData)]
    renderStreamDll.rs_awaitFrameData.restype = checkRsErrorOK

    renderStreamDll.rs_setFollower.argtypes = [ctypes.c_int]
    renderStreamDll.rs_setFollower.restype = checkRsErrorOK

    renderStreamDll.rs_beginFollowerFrame.argtypes = [ctypes.c_double]
    renderStreamDll.rs_beginFollowerFrame.restype = checkRsErrorOK

    renderStreamDll.rs_getFrameParameters.argtypes = [ctypes.c_uint64, ctypes.c_void_p, ctypes.c_uint64]
    renderStreamDll.rs_getFrameParameters.restype = checkRsErrorOK

    renderStreamDll.rs_getFrameImageData.argtypes = [ctypes.c_uint64, ctypes.POINTER(ImageFrameData), ctypes.c_uint64]
    renderStreamDll.rs_getFrameImageData.restype = checkRsErrorOK

    renderStreamDll.rs_getFrameImage2.argtypes = [ctypes.c_int64, ctypes.POINTER(SenderFrame)]
    renderStreamDll.rs_getFrameImage2.restype = checkRsErrorOK

    renderStreamDll.rs_getFrameText.argtypes = [ctypes.c_uint64, ctypes.c_uint32, ctypes.POINTER(ctypes.c_char_p)]
    renderStreamDll.rs_getFrameText.restype = checkRsErrorOK

    renderStreamDll.rs_getFrameCamera.argtypes = [StreamHandle, ctypes.POINTER(CameraData)]
    renderStreamDll.rs_getFrameCamera.restype = checkRsErrorOK

    renderStreamDll.rs_sendFrame2.argtypes = [
        StreamHandle,
        ctypes.POINTER(SenderFrame),
        ctypes.POINTER(FrameResponseData),
    ]
    renderStreamDll.rs_sendFrame2.restype = checkRsErrorOK

    renderStreamDll.rs_releaseImage2.argtypes = [ctypes.POINTER(SenderFrame)]
    renderStreamDll.rs_releaseImage2.restype = checkRsErrorOK

    renderStreamDll.rs_logToD3.argtypes = [ctypes.c_char_p]
    renderStreamDll.rs_logToD3.restype = checkRsErrorOK

    renderStreamDll.rs_sendProfilingData.argtypes = [ctypes.POINTER(ProfilingEntry), ctypes.c_int]
    renderStreamDll.rs_sendProfilingData.restype = checkRsErrorOK

    renderStreamDll.rs_setNewStatusMessage.argtypes = [ctypes.c_char_p]
    renderStreamDll.rs_setNewStatusMessage.restype = checkRsErrorOK

    return renderStreamDll


class RenderStream:
    def __init__(self):
        self.dll = loadRenderStreamFromRegistry()

        # When running under a workload, d3 redirects stdout & stderr for the workload to a file.
        # Python detects that and increases buffering to the point you don't see any output.
        # So we need to revert back to line buffering.
        # This is `TextIOWrapper` buffering, not the 'real' stream buffering.
        if os.environ.get("rsWorkloadID", None):
            sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
            sys.stderr.reconfigure(line_buffering=True, encoding="utf-8")

        self.dll.rs_initialise(VERSION_MAJOR, VERSION_MINOR)

    def __del__(self):
        try:
            self.dll.rs_shutdown()
        finally:
            # Bizarre requirement to unload explicitly.
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.FreeLibrary.argtypes = [ctypes.wintypes.HMODULE]
            kernel32.FreeLibrary(self.dll._handle)

            del self.dll

    def registerLoggingFunc(self, logger: Callable[[str], None]):
        self._logger = logger_t(lambda bMsg: logger(str(bMsg, encoding="utf-8")))
        self.dll.rs_registerLoggingFunc(self._logger)

    def registerErrorLoggingFunc(self, logger: Callable[[str], None]):
        self._errorLogger = logger_t(lambda bMsg: logger(str(bMsg, encoding="utf-8")))
        self.dll.rs_registerErrorLoggingFunc(self._errorLogger)

    def registerVerboseLoggingFunc(self, logger: Callable[[str], None]):
        self._verboseLogger = logger_t(lambda bMsg: logger(str(bMsg, encoding="utf-8")))
        self.dll.rs_registerVerboseLoggingFunc(self._verboseLogger)

    def unregisterLoggingFunc(self):
        self.dll.rs_unregisterLoggingFunc()
        del self._logger

    def unregisterErrorLoggingFunc(self):
        self.dll.rs_unregisterErrorLoggingFunc()
        del self._errorLogger

    def unregisterVerboseLoggingFunc(self):
        self.dll.rs_unregisterVerboseLoggingFunc()
        del self._verboseLogger

    def initialiseGpGpuWithoutInterop(self):
        # the pointer argument is a mistake in the API, so just pass null.
        self.dll.rs_initialiseGpGpuWithoutInterop(pID3D11Device())

    def initialiseGpGpuWithDX11Device(self, device: pID3D11Device):
        self.dll.rs_initialiseGpGpuWithDX11Device(device)

    def initialiseGpGpuWithDX11Resource(self, resource: pID3D11Resource):
        self.dll.rs_initialiseGpGpuWithDX11Resource(resource)

    def initialiseGpGpuWithDX12DeviceAndQueue(self, device: pID3D12Device, queue: pID3D12CommandQueue):
        self.dll.rs_initialiseGpGpuWithDX12DeviceAndQueue(device, queue)

    def initialiseGpGpuWithOpenGlContexts(self, glrc: ctypes.c_void_p, dc: ctypes.c_void_p):
        self.dll.rs_initialiseGpGpuWithOpenGlContexts(glrc, dc)

    def initialiseGpGpuWithVulkanDevice(self, device: VkDevice):
        self.dll.rs_initialiseGpGpuWithVulkanDevice(device)

    def useDX12SharedHeapFlag(self):
        """When working with DX12, due to the nature of some interop libraries, we either require or don't require
        the shared heap flag to be set on the resources used with RenderStream - this will tell you which."""
        value = UseDX12SharedHeapFlag()
        self.dll.rs_useDX12SharedHeapFlag(ctypes.pointer(value))
        return value

    def saveSchema(self, assetPath: str, schema: Schema):
        "Save the schema. Choose assetPath to be the location the script is run from."
        self.dll.rs_saveSchema(bytes(assetPath, encoding="utf-8"), ctypes.pointer(schema))

    def loadSchema(self, assetPath: str) -> Schema:
        "Load the schema. Choose assetPath to be the location the script is run from"
        pathBytes = bytes(assetPath, encoding="utf-8")
        nBytes = ctypes.c_uint32(0)
        try:
            self.dll.rs_loadSchema(pathBytes, pSchema(), ctypes.pointer(nBytes))
        except RenderStreamError as e:
            if e.error != RS_ERROR.BUFFER_OVERFLOW:
                raise  # we only expect buffer overflow in this case

        data = ctypes.cast((ctypes.c_byte * nBytes.value)(), pSchema)
        schema = ctypes.cast(data, pSchema)
        self.dll.rs_loadSchema(pathBytes, data, ctypes.pointer(nBytes))

        return schema.contents

    def setSchema(self, schema: Schema):
        "Set schema and fill in per-scene hash for use with rs_getFrameParameters etc"
        self.dll.rs_setSchema(ctypes.pointer(schema))

    def getStreams(self) -> StreamDescriptions:
        nBytes = ctypes.c_uint32(0)
        try:
            self.dll.rs_getStreams(pStreamDescriptions(), ctypes.pointer(nBytes))
        except RenderStreamError as e:
            if e.error != RS_ERROR.BUFFER_OVERFLOW:
                raise  # we only expect buffer overflow in this case

        data = ctypes.cast((ctypes.c_byte * nBytes.value)(), pStreamDescriptions)
        descriptions = ctypes.cast(data, pStreamDescriptions)
        self.dll.rs_getStreams(data, ctypes.pointer(nBytes))

        return descriptions.contents

    def awaitFrameData(self, timeoutMs: int) -> FrameData:
        """Waits for the system to request a frame, provides the parameters for that frame.

        In normal operation, this raises RenderStream exceptions on timeout and when streams change
        and these need to be handled appropriately."""
        frameData = FrameData()
        self.dll.rs_awaitFrameData(timeoutMs, ctypes.pointer(frameData))  # throws timout etc errors. it's ok.
        return frameData

    def setFollower(self, isFollower: bool):
        """Used to mark this node as relying on alternative mechanisms to " "distribute FrameData. Users must provide
        correct CameraResponseData to sendFrame, and call " "rs_beginFollowerFrame at the start of the frame, where
        awaitFrame would normally be called."""
        self.dll.rs_setFollower(isFollower)

    def beginFollowerFrame(self, frameTime: float):
        """Pass the engine-distributed tTracked value in, if you have " "called rs_setFollower(1) otherwise do not
        call this function."""
        self.dll.rs_beginFollowerFrame(frameTime)

    def getFrameParameters(
        self, scene: RemoteParameters
    ) -> dict[str, float | tuple[(float,) * 16] | str | ImageFrameData]:
        "returns the remote parameters for this frame."
        nFloats = 0
        nImages = 0
        nTexts = 0
        for i in range(scene.nParameters):
            param: RemoteParameter = scene.parameters[i]
            type = param.type

            if param.flags & RemoteParameterFlags.READ_ONLY.value:
                continue  # don't count output params

            if type == RemoteParameterType.NUMBER:
                nFloats += 1
            elif type == RemoteParameterType.IMAGE:
                nImages += 1
            elif type == RemoteParameterType.POSE:
                nFloats += 16
            elif type == RemoteParameterType.TRANSFORM:
                nFloats += 16
            elif type == RemoteParameterType.TEXT:
                nTexts += 1
            else:
                raise Exception(f"Unknown remote parameter type {type}")

        floats = (ctypes.c_float * nFloats)()
        self.dll.rs_getFrameParameters(scene.hash, floats, ctypes.sizeof(floats))
        images = (ImageFrameData * nImages)()
        self.dll.rs_getFrameImageData(scene.hash, images, ctypes.sizeof(images))

        values = {}
        iFloat = 0
        iImage = 0
        iText = 0
        for i in range(scene.nParameters):
            param: RemoteParameter = scene.parameters[i]

            if param.flags & RemoteParameterFlags.READ_ONLY.value:
                continue  # don't count output params

            key = str(param.key, encoding="utf-8")
            if param.type == RemoteParameterType.NUMBER:
                values[key] = floats[iFloat]
                iFloat += 1
            elif param.type == RemoteParameterType.IMAGE:
                values[key] = images[iImage]
                iImage += 1
            elif param.type == RemoteParameterType.POSE:
                values[key] = tuple(floats[iFloat : iFloat + 16])
                iFloat += 16
            elif type == RemoteParameterType.TRANSFORM:
                values[key] = tuple(floats[iFloat : iFloat + 16])
                iFloat += 16
            elif type == RemoteParameterType.TEXT:
                stringMem = ctypes.c_char_p()
                self.dll.rs_getFrameText(scene.hash, iText, ctypes.pointer(stringMem))
                values[key] = str(stringMem, encoding="utf-8")
                iText += 1
            else:
                raise Exception(f"Unknown remote parameter type {type}")

        return values

    def getFrameImage(self, imageId: ctypes.c_int64, frame: SenderFrame):
        "fills in (frameData) with the remote image."
        self.dll.rs_getFrameImage2(imageId, ctypes.pointer(frame))

    def getFrameCamera(self, stream: StreamHandle) -> CameraData:
        """returns the CameraData for this stream, or RS_ERROR_NOTFOUND if no " "camera data is available for this
        stream on this frame"""
        cam = CameraData()
        self.dll.rs_getFrameCamera(stream, ctypes.pointer(cam))
        return cam

    def sendFrame(self, stream: StreamHandle, frame: SenderFrame, response: FrameResponseData):
        "publish a frame buffer which was generated from the associated tracking and timing information."
        self.dll.rs_sendFrame2(stream, ctypes.pointer(frame), ctypes.pointer(response))

    def releaseImage(self, frame: SenderFrame):
        "release any references to image (e.g. before deletion)"
        self.dll.rs_releaseImage2(ctypes.pointer(frame))

    def logToD3(self, message):
        """Log text back to the controlling d3 instance, this will be presented as a single line.

        Do not terminate with a newline character"""
        self.dll.rs_logToD3(bytes(message, encoding="utf-8"))

    def sendProfilingData(self, entries: list[ProfilingEntry]):
        self.dll.rs_sendProfilingData((ProfilingEntry * len(entries))(*entries))

    def setNewStatusMessage(self, message):
        self.dll.rs_setNewStatusMessage(bytes(message, encoding="utf-8"))
