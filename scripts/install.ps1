# Define the Python installer details
$pyinstaller_zip = 'python-3.10.11-embed-amd64.zip'
$pyinstaller_url = "https://www.python.org/ftp/python/3.10.11/$pyinstaller_zip"
$pyinstaller_local = "$env:TEMP\$pyinstaller_zip"

# Check if the installer already exists in the temp folder
if (-Not (Test-Path $pyinstaller_local)) {
    Write-Output "Downloading Python..."
    Invoke-WebRequest $pyinstaller_url -OutFile $pyinstaller_local
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

# Customization for enabling RS workload behaviour and per-asset packages
@'
import os
import sys
import subprocess

# When running under a workload, d3 redirects stdout & stderr for the workload to a file.
# Python detects that and increases buffering to the point you don't see any output.
# So we need to revert back to line buffering.
# This is `TextIOWrapper` buffering, not the 'real' stream buffering.
if os.environ.get("rsWorkloadID", None):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
    sys.stderr.reconfigure(line_buffering=True, encoding="utf-8")


# If a pyrs script is given, run in that folder. Important when running as a RS workload.
if len(sys.argv) > 0 and sys.argv[0].endswith('.pyrs'):
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(script_dir)


# If we are working on or near a .pyrs asset, ensure requirements are met
# and add the dependencies site package.
from glob import glob
if glob("*.pyrs"):
    # Construct the path to the requirements.txt file
    requirements_path = os.path.abspath('requirements.txt')
    package_path = os.path.abspath("pyrs_packages")

    if sys.argv[:2] != ['-m', 'install']:
        # Check if the requirements.txt file exists 
        if os.path.exists(requirements_path):
            print(f"requirements.txt found. Installing packages...")

            # Build the pip install command
            pip_command = [
                sys.executable, "-m", "pip", "install", "-r", requirements_path,
                "--prefix", package_path, "--no-compile"
            ]

            try:
                subprocess.check_call(pip_command)
            except subprocess.CalledProcessError as e:
                print(f"An error occurred while installing packages: {e}")
        else:
            print(f"No requirements.txt found in {os.getcwd()}.")

    # Append the installed packages to sys.path, whether or not requirements is present.
    if os.path.exists(package_path):
        import site
        sys.prefix = package_path
        site.addsitedir(os.path.join(package_path, "Lib", "site-packages"))


# Ensure we are always able to import from the current directory
sys.path.insert(0, '')
'@ | Set-Content -Path "$installFolder\sitecustomize.py" -Encoding Ascii

# Define the path to the installed Python executable
$pythonExe = "$installFolder\python.exe"

# Install pip
$get_pip = "$env:TEMP\get-pip.py"
if (-Not (Test-Path $get_pip)) {
    Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile $get_pip
}
& $pythonExe $get_pip --no-warn-script-location

# Install packaging requirement for renderstream
& $pythonExe -m pip install hatchling --no-warn-script-location


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

# Define the path to the permitted_custom_extensions.txt file
$extensionsFilePath = Join-Path $renderStreamProjectsFolder "permitted_custom_extensions.txt"

# Check if the file exists and contains the 'pyrs' line
if (-Not (Test-Path $extensionsFilePath)) {
    "pyrs" | Set-Content -Path $extensionsFilePath -Encoding Ascii
} else {
    $existingContent = Get-Content -Path $extensionsFilePath
    if (-Not ($existingContent -contains "pyrs")) {
        Add-Content -Path $extensionsFilePath -Value "pyrs"
    }
}


Write-Output "Associated .pyrs files with engine"
Write-Output "RenderStream engine installation completed."
