if __name__ == "__main__":
    # use the local version of renderstream
    import sys
    import os.path as p

    sys.path.insert(0, p.join(p.dirname(p.dirname(__file__)), "src"))

import renderstream as RS
import glm
from OpenGL.WGL import wglGetCurrentContext, wglGetCurrentDC
from OpenGL.GLUT import *
from OpenGL.GL import *
from OpenGL.GL import shaders
import numpy as np
from ctypes import c_void_p


VERTEX_SHADER = """#version 330

uniform mat4 MVP;

in vec4 attrib_Position;
in vec4 attrib_Color;

out vec4 attrib_Frag_Color;

void main()
{
    gl_Position = MVP * attrib_Position;
    attrib_Frag_Color = attrib_Color;
}
"""

FRAGMENT_SHADER = """#version 330

in vec4 attrib_Frag_Color;

void main()
{
    gl_FragColor = attrib_Frag_Color;
}
"""

shaderProgram = None


def initGL(rs):
    global shaderProgram

    vertexshader = shaders.compileShader(VERTEX_SHADER, GL_VERTEX_SHADER)
    fragmentshader = shaders.compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)

    shaderProgram = shaders.compileProgram(vertexshader, fragmentshader)

    triangles = [-0.5, -0.5, 0.5, 0, 0, 1, 1,   # fbl
                 0.5, -0.5, 0.5, 0, 1, 0, 1,    # fbr
                 -0.5, 0.5, 0.5, 1, 0, 0, 1,    # ftl
                 0.5, 0.5, 0.5, 1, 1, 0, 1,     # ftr
                 -0.5, -0.5, -0.5, 0, 1, 1, 1,  # bbl
                 0.5, -0.5, -0.5, 1, 1, 0, 1,   # bbr
                 -0.5, 0.5, -0.5, 1, 0, 1, 1,   # btl
                 0.5, 0.5, -0.5, 1, 1, 1, 1,    # btr
                 ]
    triangles = np.array(triangles, dtype=np.float32)
    
    vertexArray = glGenVertexArrays(1)
    glBindVertexArray(vertexArray)

    vertexBuffer = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)
    glBufferData(GL_ARRAY_BUFFER, triangles.nbytes, triangles, GL_STATIC_DRAW)

    attrib_Position = glGetAttribLocation(shaderProgram, 'attrib_Position')
    glVertexAttribPointer(attrib_Position, 3, GL_FLOAT, GL_FALSE, 7 * 4, c_void_p(0))
    glEnableVertexAttribArray(attrib_Position)

    attrib_Color = glGetAttribLocation(shaderProgram, 'attrib_Color')
    glVertexAttribPointer(attrib_Color, 4, GL_FLOAT, GL_FALSE, 7 * 4, c_void_p(3*4))
    glEnableVertexAttribArray(attrib_Color)

    indices = [0, 2, 1, 1, 3, 2, # front
               0, 2, 4, 6, 2, 4, # left
               1, 3, 5, 7, 3, 5, # right
               0, 1, 4, 5, 1, 4, # bottom
               2, 3, 6, 7, 6, 3, # top
               4, 5, 6, 7, 5, 6] # back
    indices = np.array(indices, dtype=np.int16)
    
    IBO = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, IBO)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)


schema = None
streams = None
streamTextures = []
streamFrameBuffers = []


def allocStreamTextures():
    global renderTargets, streamTextures, streamFrameBuffers

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
        glBindTexture( GL_TEXTURE_2D, 0 )

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


def render(rs):
    global streams

    try:
        frameData = rs.awaitFrameData(5000)
    except RS.RenderStreamError as e:
        if e.error == RS.RS_ERROR.STREAMS_CHANGED:
            streams = rs.getStreams()
            allocStreamTextures()
            return
        elif e.error == RS.RS_ERROR.TIMEOUT:
            return
        else:
            raise

    for iStream in range(streams.nStreams):
        stream: RS.StreamDescription = streams.streams[iStream]

        streamCam = RS.CameraResponseData()
        streamCam.tTracked = frameData.tTracked
        try:
            streamCam.camera = rs.getFrameCamera(stream.handle)
        except RS.RenderStreamError as e:
            if e.error == RS.RS_ERROR.NOT_FOUND:
                # on startup, this workload may not have been found on the controller yet.
                # so the frame request didn't include this stream.
                continue
            else:
                raise

        # untracked camera
        if streamCam.camera.cameraHandle == 0:
            streamCam.camera.z = -5
                
        scene = schema.scenes.scenes[frameData.scene]
        paramValues = rs.getFrameParameters(scene)

        # Set up projection matrix
        nearZ = streamCam.camera.nearZ
        farZ = streamCam.camera.farZ

        if streamCam.camera.orthoWidth > 0.0:
            cameraAspect = streamCam.camera.sensorX / streamCam.camera.sensorY
            imageWidth = streamCam.camera.orthoWidth
            imageHeight = imageWidth / cameraAspect
        else:
            imageWidth = (streamCam.camera.sensorX / streamCam.camera.focalLength) * nearZ
            imageHeight = (streamCam.camera.sensorY / streamCam.camera.focalLength) * nearZ

        l = (-0.5 + stream.clipping.left) * imageWidth
        r = (-0.5 + stream.clipping.right) * imageWidth
        t = (-0.5 + 1.0 - stream.clipping.top) * imageHeight
        b = (-0.5 + 1.0 - stream.clipping.bottom) * imageHeight

        if streamCam.camera.orthoWidth > 0.0:
            proj = glm.ortho(l, r, t, b, nearZ, farZ)
        else:
            proj = glm.frustum(l, r, t, b, nearZ, farZ)

        # Set up camera view matrix
        rad = glm.radians
        rz = glm.rotate(rad(streamCam.camera.rz), glm.vec3(0, 0, -1))
        rx = glm.rotate(rad(streamCam.camera.rx), glm.vec3(1, 0, 0))
        ry = glm.rotate(rad(streamCam.camera.ry), glm.vec3(0, -1, 0))
        camRotation = ry * rx * rz
        camTranslation = glm.translate(glm.vec3(streamCam.camera.x, streamCam.camera.y, -streamCam.camera.z))
        view = glm.transpose(camRotation) * glm.inverse(camTranslation)

        glBindFramebuffer(GL_FRAMEBUFFER, streamFrameBuffers[iStream])

        glEnable(GL_DEPTH_TEST)
        glClearColor(0, 0, 0, 0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glViewport(0, 0, stream.width, stream.height)

        glUseProgram(shaderProgram)
        
        # Set up model matrix
        model = glm.rotate(rad(frameData.tTracked * paramValues["cube_spin_speed"]), glm.vec3(0, 1, 0))

        MVP = proj * view * model
        glUniformMatrix4fv(glGetUniformLocation(shaderProgram, "MVP"), 1, GL_FALSE, glm.value_ptr(MVP))

        # Actually draw the cube
        glDrawElements(GL_TRIANGLES, 6 * 6, GL_UNSIGNED_SHORT, c_void_p(0))

        glFinish()

        response = RS.FrameResponseData(streamCam, scene, {})

        glData = RS.OpenGlData()
        glData.texture = streamTextures[iStream]
        rs.sendFrame(stream.handle, RS.SenderFrame(glData), response)

        glUseProgram(0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)


def main():
    rs = RS.RenderStream()
    
    global schema
    schema = RS.Schema(
        [""],
        [
            RS.RemoteParameters("Default", [
                RS.RemoteParameter(
                    "cube_spin_speed",
                    "Cube spin speed",
                    "Effect properties",
                    RS.NumericalDefaults(45.0, 0.0, 90.0, 1.0)
                ),
            ])
        ],
        engineName="RenderStream-PY OpenGL example",
        engineVersion="0",
        info="sample application to demonstrate RenderStream-py")
    rs.saveSchema(__file__, schema)
    rs.setSchema(schema)

    glutInit([])
    glutInitDisplayMode(GLUT_RGB | GLUT_DEPTH | GLUT_SINGLE)
    glutInitWindowSize(640, 480)
    window = glutCreateWindow(b"offscreen")
    
    rs.initialiseGpGpuWithOpenGlContexts(wglGetCurrentContext(), wglGetCurrentDC())

    initGL(rs)
    def idleCallback(): # needs to be kept alive
        nonlocal rs

        try:
            render(rs)
        except RS.RenderStreamError as e:
            if e.error != RS.RS_ERROR.QUIT:
                import traceback as tb
                tb.print_exc()
            else:
                print("Exiting normally")

            del rs # shutdown renderstream before glut since glut does something to the network stack
            glutDestroyWindow(window)
            glutMainLoopEvent()
        except:
            import traceback as tb
            tb.print_exc()

            del rs # shutdown renderstream since glut does something to the network stack
            glutDestroyWindow(window)
            glutMainLoopEvent()

    def displayCallback():
        pass # actually we render in idle, but glut is unhappy if this isn't registered

    glutDisplayFunc(displayCallback)
    glutIdleFunc(idleCallback)
    glutMainLoop()
    print("Exited main loop")

if __name__ == '__main__':
    main()
