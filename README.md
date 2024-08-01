# RenderStream-py
Python bindings for the RenderStream API, installable as an engine for .pyrs RenderStream applications.

## Installing the engine

On every RX or development workstation which uses .pyrs RenderStream assets, the engine needs to be installed. To install, follow the steps below:

1. Open Windows PowerShell
2. Run `iex (iwr https://github.com/disguise-one/RenderStream-py/raw/r1.31/scripts/install.ps1).Content`

The engine is installed into `RenderStream Engines` which is a sibling folder of `RenderStream Projects`. It currently uses python 3.10, as some common packages are not yet compatible with later versions of Python. The bindings themselves are compatible with any Python version >= 3.7

## Testing the engine

The engine is associated with `.pyrs` file extensions. There are example .pyrs assets in the samples folder of this repository. Copy the whole samples folder to your `RenderStream Projects` folder. The `cube` and `schema` RenderStream assets should appear immediately. [Configure a RenderStream layer](https://help.disguise.one/designer/layers/layer-types/content/renderstream-layer#config) to use the asset.

## Installing asset dependencies

Adding a [`requirements.txt`](https://pip.pypa.io/en/stable/user_guide/#requirements-files) in the same folder as a `.pyrs` asset will allow dependencies to be installed in a `pyrs_packages` folder next to the `.pyrs` script file. This folder can be copied as-is across RX machines.