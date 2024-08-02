from ctypes import c_void_p
from OpenGL.GL import *
import renderstream as RS
import glfw
import glm
from win32gui import GetDC

def allocStreamTextures(streams: RS.StreamDescriptions):
    streamTextures = []
    streamFrameBuffers = []
    
    for iStream in range(streams.nStreams):
        stream: RS.StreamDescription = streams.streams[iStream]

        # colour
        texture = glGenTextures(1)
        streamTextures.append(texture)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, stream.width, stream.height, 0, GL_BGRA, GL_UNSIGNED_BYTE, c_void_p(0))
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL)
        glBindTexture(GL_TEXTURE_2D, 0 )

        # depth
        depth = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, depth)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, stream.width, stream.height, 0, GL_DEPTH_COMPONENT, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL)
        glBindTexture( GL_TEXTURE_2D, 0 )

        # framebuffer
        frameBuffer = glGenFramebuffers(1)
        streamFrameBuffers.append(frameBuffer)

        glBindFramebuffer(GL_FRAMEBUFFER, frameBuffer)
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, texture, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth, 0)  
        glDrawBuffers([GL_COLOR_ATTACHMENT0])

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise Exception("Failed fame buffer status check")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        
    assert(len(streamTextures) == streams.nStreams)
    assert(len(streamFrameBuffers) == streams.nStreams)
    return streamTextures, streamFrameBuffers

def initWithOffscreenGLWindow(rs: RS.RenderStream):
    # Initialize the library
    glfw.init()
    # Set window hint NOT visible
    glfw.window_hint(glfw.VISIBLE, False)
    # Create a windowed mode window and its OpenGL context
    window = glfw.create_window(10, 10, "renderstream shadertoy", None, None)

    # Make the window's context current
    glfw.make_context_current(window)
    
    hrc = glfw.get_wgl_context(window)
    hdc = GetDC(glfw.get_win32_window(window))

    rs.initialiseGpGpuWithOpenGlContexts(hrc, hdc)

def getCameraViewProjMatrices(cam: RS.CameraData, clipping: RS.ProjectionClipping):
    nearZ = cam.nearZ
    farZ = cam.farZ

    if cam.orthoWidth > 0.0:
        cameraAspect = cam.sensorX / cam.sensorY
        imageWidth = cam.orthoWidth
        imageHeight = imageWidth / cameraAspect
    else:
        imageWidth = (cam.sensorX / cam.focalLength) * nearZ
        imageHeight = (cam.sensorY / cam.focalLength) * nearZ

    l = (-0.5 + clipping.left) * imageWidth
    r = (-0.5 + clipping.right) * imageWidth
    t = (-0.5 + 1.0 - clipping.top) * imageHeight
    b = (-0.5 + 1.0 - clipping.bottom) * imageHeight

    if cam.orthoWidth > 0.0:
        proj = glm.ortho(l, r, t, b, nearZ, farZ)
    else:
        proj = glm.frustum(l, r, t, b, nearZ, farZ)

    rad = glm.radians
    rz = glm.rotate(rad(cam.rz), glm.vec3(0, 0, -1))
    rx = glm.rotate(rad(cam.rx), glm.vec3(1, 0, 0))
    ry = glm.rotate(rad(cam.ry), glm.vec3(0, -1, 0))
    camRotation = ry * rx * rz
    camTranslation = glm.translate(glm.vec3(cam.x, cam.y, -cam.z))
    view = glm.transpose(camRotation) * glm.inverse(camTranslation)

    return view, proj

def appLoop(rs: RS.RenderStream, initGL, render):
    initWithOffscreenGLWindow(rs)

    initGL()
    
    streams: RS.StreamDescriptions = None
    streamTextures = []
    streamFrameBuffers = []

    while True:
        try:
            frameData = rs.awaitFrameData(5000)

            for iStream in range(streams.nStreams):
                stream: RS.StreamDescription = streams.streams[iStream]

                glBindFramebuffer(GL_FRAMEBUFFER, streamFrameBuffers[iStream])

                response = render(rs, frameData, stream)

                glData = RS.OpenGlData()
                glData.texture = streamTextures[iStream]
                rs.sendFrame(stream.handle, RS.SenderFrame(glData), response)
        except RS.RenderStreamError as e:
            if e.error == RS.RS_ERROR.STREAMS_CHANGED:
                streams = rs.getStreams()
                streamTextures, streamFrameBuffers = allocStreamTextures(streams)
                continue
            elif e.error == RS.RS_ERROR.TIMEOUT:
                continue
            elif e.error != RS.RS_ERROR.QUIT:
                import traceback as tb
                tb.print_exc()
                break
            else:
                print("Exiting normally")
                break
        except:
            import traceback as tb
            tb.print_exc()
            break
