if __name__ == "__main__":
    # use the local version of renderstream
    import sys
    import os.path as p

    sys.path.insert(0, p.join(p.dirname(p.dirname(__file__)), "src"))

import renderstream as RS
import numpy as np
import ctypes


def getSchema(rs):
    schema = rs.loadSchema(__file__)
    if schema.scenes.nScenes == 0:
        # This represents some 'editor time' generation of the schema (actually here it happens on first run)
        # We only need one of either the loadSchema or the set&saveSchema functions to be called in a given
        # run of the application.
        print("Creating new schema")
        schema = RS.Schema(
            ["chanchan"],
            [
                RS.RemoteParameters(
                    "Strobe",
                    [
                        RS.RemoteParameter(
                            "stable_shared_key_speed",
                            "Strobe speed",
                            "Shared properties",
                            RS.NumericalDefaults(1.0, 0.0, 4.0, 0.01),
                            flags=RS.RemoteParameterFlags.NO_SEQUENCE,
                        ),
                        RS.RemoteParameter(
                            "stable_key_colour_r",
                            "Colour R",
                            "Strobe properties",
                            RS.NumericalDefaults(1.0, 0.0, 1.0, 0.001),
                        ),
                        RS.RemoteParameter(
                            "stable_key_colour_g",
                            "Colour G",
                            "Strobe properties",
                            RS.NumericalDefaults(1.0, 0.0, 1.0, 0.001),
                        ),
                        RS.RemoteParameter(
                            "stable_key_colour_b",
                            "Colour B",
                            "Strobe properties",
                            RS.NumericalDefaults(1.0, 0.0, 1.0, 0.001),
                        ),
                        RS.RemoteParameter(
                            "stable_key_colour_a",
                            "Colour A",
                            "Strobe properties",
                            RS.NumericalDefaults(1.0, 0.0, 1.0, 0.001),
                        ),
                        RS.RemoteParameter(
                            "stable_key_strobe_ro",
                            "Strobe",
                            "Strobe properties",
                            RS.NumericalDefaults(1.0, 0.0, 1.0, 0.001),
                            flags=RS.RemoteParameterFlags.READ_ONLY,
                        ),
                    ],
                ),
                RS.RemoteParameters(
                    "Radar",
                    [
                        RS.RemoteParameter(
                            "stable_shared_key_speed",
                            "Radar speed",
                            "Shared properties",
                            RS.NumericalDefaults(1.0, 0.0, 4.0, 0.01),
                            flags=RS.RemoteParameterFlags.NO_SEQUENCE,
                        ),
                        RS.RemoteParameter(
                            "stable_key_length",
                            "Length",
                            "Radar properties",
                            RS.NumericalDefaults(0.25, 0.0, 1.0, 0.01),
                        ),
                        RS.RemoteParameter(
                            "stable_key_direction",
                            "Direction",
                            "Radar properties",
                            RS.NumericalDefaults(1.0, 0.0, 1.0, 1),
                            ["Left", "Right"],
                        ),
                    ],
                ),
            ],
            engineName="Schema sample",
            engineVersion="9000+",
            info="sample application to demonstrate RenderStream-py",
        )
        rs.saveSchema(__file__, schema)
        rs.setSchema(schema)
    return schema


def rs_log(message):
    print(message)


def main():
    rs = RS.RenderStream()

    # rs.registerLoggingFunc(rs_log)
    # rs.registerErrorLoggingFunc(rs_log)
    # rs.registerVerboseLoggingFunc(rs_log)
    rs.initialiseGpGpuWithoutInterop()

    schema = getSchema(rs)
    streams = None

    print("Starting main loop")
    while True:
        try:
            frameData = rs.awaitFrameData(5000)
        except RS.RenderStreamError as e:
            if e.error == RS.RS_ERROR.STREAMS_CHANGED:
                streams = rs.getStreams()
                continue
            elif e.error == RS.RS_ERROR.TIMEOUT:
                continue
            elif e.error == RS.RS_ERROR.QUIT:
                break
            else:
                raise

        if frameData.scene >= schema.scenes.nScenes:
            print("out of bounds")
            continue

        # 'load' the scene we are requested to, and get the
        # dynamic params we need to run it
        scene = schema.scenes.scenes[frameData.scene]
        paramValues = rs.getFrameParameters(scene)

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

            totalCanvasWidthPx = int(stream.width / (stream.clipping.right - stream.clipping.left))
            #  totalCanvasHeightPx = int(stream.height / (stream.clipping.bottom - stream.clipping.top))
            streamOffsetXPx = int(stream.clipping.left * totalCanvasWidthPx)

            speed = paramValues["stable_shared_key_speed"]
            if frameData.scene == 0:
                r, g, b, a = (
                    paramValues["stable_key_colour_r"],
                    paramValues["stable_key_colour_g"],
                    paramValues["stable_key_colour_b"],
                    paramValues["stable_key_colour_a"],
                )
                strobe = abs(1 - ((frameData.localTime * speed) % 2))
                colour = np.array(
                    (b * strobe * 255, g * strobe * 255, r * strobe * 255, a * strobe * 255), dtype=np.uint8
                )
                frameBuffer = np.tile(colour, stream.width * stream.height)
                outputParams = {"stable_key_strobe_ro": strobe}
            else:
                lengthPx = int(paramValues["stable_key_length"] * totalCanvasWidthPx)
                direction = paramValues["stable_key_direction"]

                xStartRadar = int(frameData.localTime * speed * totalCanvasWidthPx)
                xStartRadar = xStartRadar if direction else -xStartRadar

                lineBrightness = np.zeros(stream.width, dtype=np.uint8)
                for offset in range(lengthPx):
                    fade = int(255 * (lengthPx - offset) / lengthPx)
                    x = int(xStartRadar - offset if direction else xStartRadar + offset) % totalCanvasWidthPx
                    streamX = x - streamOffsetXPx
                    if streamX >= 0 and streamX < stream.width:
                        lineBrightness[streamX] = fade
                lineBytes = lineBrightness.repeat(4)
                frameBuffer = np.tile(lineBytes, stream.height)
                outputParams = {}

            hostPixels = RS.HostMemoryData()
            hostPixels.data = frameBuffer.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
            hostPixels.stride = stream.width * 4
            hostPixels.format = RS.RSPixelFormat.BGRA8

            response = RS.FrameResponseData(streamCam, scene, outputParams)

            rs.sendFrame(stream.handle, RS.SenderFrame(hostPixels), response)


if __name__ == "__main__":
    main()
