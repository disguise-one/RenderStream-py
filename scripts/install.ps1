# Define the Python installer details
$pyinstaller_zip = 'python-3.10.11-embed-amd64.zip'
$pyinstaller_url = "https://www.python.org/ftp/python/3.10.11/$pyinstaller_zip"
$pyinstaller_local = "$env:TEMP\$pyinstaller_zip"

# Check if the installer already exists in the temp folder
if (-Not (Test-Path $pyinstaller_local)) {
    Write-Output "Downloading Python..."
    Invoke-WebRequest $pyinstaller_url -OutFile $pyinstaller_local
} else {
    Write-Output "Python installer already exists in the temp folder."
}

# Retrieve the path from the registry
$regKey = 'HKCU:\Software\d3 Technologies\d3 Production Suite'
$regValue = 'RenderStream Projects Folder'
$renderStreamProjectsFolder = (Resolve-Path (Get-ItemProperty -Path $regKey).$regValue).Path
if (-Not (Test-Path $renderStreamProjectsFolder)) {
    Write-Error "No renderstream projects folder - d3 not installed?"
    exit 1
}

# Navigate to the parent folder and define the target installation path
$parentFolder = Split-Path -Parent $renderStreamProjectsFolder
$installFolder = Join-Path $parentFolder "RenderStream Engines\RenderStream-py"

# Create the necessary directories if they don't exist
if (-Not (Test-Path $installFolder)) {
    Write-Output "Creating installation directory: $installFolder"
    New-Item -Path $installFolder -ItemType Directory -Force
} else {
    Write-Output "Installation directory already exists: $installFolder"
}

Expand-Archive -Path $pyinstaller_local -DestinationPath $installFolder -Force

# Enable site-packages
$pthFile = Join-Path $installFolder "python310._pth"
$pthContent = Get-Content -Path $pthFile
$pthContent = $pthContent -replace '^#import site', 'import site'
Set-Content -Path $pthFile -Value $pthContent

# Enable local imports for .pyrs scripts
# Define the content you want to write to sitecustomize.py
$sitecustomizeContent = @'
import sys, os

if len(sys.argv) > 0 and sys.argv[0].endswith(".pyrs"):
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    sys.path.insert(0, script_dir)

sys.path.insert(0, "") # "current folder" lookup
'@

# Write the content to the file using ASCII encoding
$sitecustomizeContent | Set-Content -Path "$installFolder\sitecustomize.py" -Encoding Ascii

# Define the path to the installed Python executable
$pythonExe = "$installFolder\python.exe"

# Install pip
Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile $env:TEMP\get-pip.py
& $pythonExe $env:TEMP\get-pip.py --no-warn-script-location

# Install common packages
& $pythonExe -m pip install PyOpenGL PyGLM numpy hatchling --no-warn-script-location


# Define the RenderStream package download details
$repo = "RenderStream-py"
$version = "r1.31"
$rs_package_url = "https://github.com/disguise-one/$repo/archive/refs/heads/$version.zip"
$rs_package_zip = "$env:TEMP\rspy.zip"

# Download the RenderStream package
Write-Output "Downloading RenderStream package..."
Invoke-WebRequest $rs_package_url -OutFile $rs_package_zip

# Define the extraction path
$rs_package_extract_path = "$env:TEMP\rspy"

# Extract the downloaded ZIP file
Write-Output "Extracting RenderStream package..."
Expand-Archive -Path $rs_package_zip -DestinationPath $rs_package_extract_path -Force

# Change directory to the extracted package folder
$extracted_folder_name = "$repo-$version"  # Adjust if necessary based on the extracted folder name
$package_folder = Join-Path $rs_package_extract_path $extracted_folder_name

# Install the package using the installed Python
Write-Output "Installing RenderStream package using pip..."
& $pythonExe -m pip install $package_folder

# Install FreeGlut
$freeglut_zip = "$env:TEMP\freeglut.zip"
Invoke-WebRequest "https://www.transmissionzero.co.uk/files/software/development/GLUT/freeglut-MSVC.zip" -OutFile $freeglut_zip

# Define paths for the extracted FreeGlut files and the target destination
$freeglut_extract_path = "$env:TEMP\freeglut"
$freeglut_dll_source = "freeglut\bin\x64\freeglut.dll"
$freeglut_dll_target = "$installFolder\Lib\site-packages\OpenGL\DLLs\freeglut64.vc14.dll"

# Extract the full FreeGlut ZIP file
Write-Output "Fixing OpenGL..."
Expand-Archive -Path $freeglut_zip -DestinationPath $freeglut_extract_path -Force

# Copy the specific DLL file to the target location
$source_dll_path = Join-Path $freeglut_extract_path $freeglut_dll_source
if (Test-Path $source_dll_path) {
    $target_dll_folder = Split-Path $freeglut_dll_target -Parent
    if (-Not (Test-Path $target_dll_folder)) {
        New-Item -Path $target_dll_folder -ItemType Directory -Force | Out-Null
    }
    Copy-Item -Path $source_dll_path -Destination $freeglut_dll_target -Force
} else {
    Write-Output "Error: $source_dll_path not found."
}

# Define the file extension and associated application
$extension = ".pyrs"
$fileType = "Python.RenderStream"

# Define the registry keys and values
$regKey_Extension = "HKCU:\Software\Classes\$extension"
$regKey_FileType = "HKCU:\Software\Classes\$fileType\shell\open\command"

# Associate the extension with a file type
New-Item -Path $regKey_Extension -Force | Out-Null
Set-ItemProperty -Path $regKey_Extension -Name "(Default)" -Value $fileType

# Set the command to open the file type with the installed Python executable
$command = "`"$pythonExe`" `"%1`""
New-Item -Path $regKey_FileType -Force | Out-Null
Set-ItemProperty -Path $regKey_FileType -Name "(Default)" -Value $command

Write-Output "Associated .pyrs files with engine"
Write-Output "RenderStream engine installation completed."

# Check if requirements.txt exists and install dependencies
$scriptPath = $MyInvocation.MyCommand.Path
$scriptDirectory = Split-Path -Parent $scriptPath
$requirementsFile = Join-Path $scriptDirectory "requirements.txt"
if (Test-Path $requirementsFile) {
    Write-Output "Found requirements.txt, installing dependencies..."
    & $pythonExe -m pip --disable-pip-version-check install -r $requirementsFile --no-warn-script-location
    Write-Output "Dependencies installed from requirements.txt"
} else {
    Write-Output "No requirements.txt found. Skipping additional package installation."
}
