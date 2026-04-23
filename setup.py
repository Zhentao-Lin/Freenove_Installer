import subprocess
from pathlib import Path
import requests
import time
import os
from typing import Union
import shutil 
import sys

class LibraryInstaller:
    def __init__(self):
        self.kit_code = None
        self.connector_version = None
        self.board_version = None
        self.camera_version = None
        self.camera_port = None
        self.config = {
            'kit_code': self.kit_code,
            'connector_version': self.connector_version if self.kit_code in ['FNK0043', 'FNK0050', 'FNK0052'] else None,
            'board_version': self.board_version if self.kit_code == 'FNK0077' else None,
            'camera_version': self.camera_version,
            'camera_port': self.camera_port
        }
        self.debug_output_enabled = True

    def detect_platform(self):
        """
        Detect the type of operating system platform
        """
        import platform
        
        system = platform.system().lower()
        
        if system == "windows":
            platform_info = "Windows"
            print(f"Detected Operating System: {platform_info}")
            return "windows"
        elif system == "darwin":
            platform_info = "Mac OS"
            print(f"Detected Operating System: {platform_info}")
            return "macos"
        elif system == "linux":
            # Further check if it's a Raspberry Pi
            try:
                with open('/sys/firmware/devicetree/base/model', 'r') as f:
                    model = f.read().strip().lower()
                    if 'raspberry' in model:
                        print(f"Detected Operating System: Linux (Raspberry Pi - {model})")
                        return "raspberry_pi"
                    else:
                        print(f"Detected Operating System: Linux ({model})")
                        return "linux"
            except FileNotFoundError:
                # If the specific Raspberry Pi file is not found, it's a general Linux system
                distro = ""
                try:
                    # Try to get Linux distribution information
                    with open('/etc/os-release', 'r') as f:
                        for line in f:
                            if line.startswith('PRETTY_NAME'):
                                distro = line.split('=')[1].strip().strip('"')
                                break
                except FileNotFoundError:
                    pass
                    
                if distro:
                    print(f"Detected Operating System: Linux ({distro})")
                else:
                    print(f"Detected Operating System: Linux")
                return "linux"
        else:
            platform_info = platform.system()
            print(f"Detected Unknown Operating System: {platform_info}")
            return "unknown"
    
    def get_raspberry_pi_version(self) -> int:
        try:
            with open('/sys/firmware/devicetree/base/model', 'r') as f:
                model = f.read().strip()
                if "Raspberry Pi 5" in model:
                    return 5
                elif "Raspberry Pi 4" in model:
                    return 4
                elif "Raspberry Pi 3" in model:
                    return 3
                elif "Raspberry Pi 2" in model:
                    return 2
                else:
                    return 1
        except Exception as e:
            print(f"Error getting Raspberry Pi version: {e}")
            return 0
    
    def run_command_with_output(self, cmd, show_output: bool = True) -> bool:
        try:
            if isinstance(cmd, list):
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, 
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    shell=False
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    shell=True
                )
            
            for line in iter(process.stdout.readline, ''):
                if show_output:
                    print(line.rstrip())
                    sys.stdout.flush()
            
            process.stdout.close()
            process.wait()
            
            return process.returncode == 0
        except Exception as e:
            print(f"Command execution error: {e}")
            return False
    
    def update_submodules(self, submodule_names=None) -> bool:
        try:
            if submodule_names is None:
                print("\nUpdating all submodules. Please wait, this may take a while...")
                success = self.run_command_with_output(['git', 'submodule', 'update', '--init', '--recursive'], self.debug_output_enabled)
            else:
                library_modules = ['mpu6050', 'rpi-ws281x-python', 'utils']
                
                submodules_to_update = []
                for name in submodule_names:
                    if name in library_modules:
                        submodules_to_update.append(f'libraries/{name}')
                    else:
                        if name.startswith(('FNK', 'Freenove')):  
                            submodules_to_update.append(f'codes/{name}') 
                        else:
                            if os.path.exists(f'libraries/{name}'):
                                submodules_to_update.append(f'libraries/{name}')
                            else:
                                print(f"Warning: Invalid submodule name '{name}' ignored.")
                
                if not submodules_to_update:
                    print("No valid submodules to update.")
                    return True
                
                print(f"\nUpdating submodules: {', '.join(submodules_to_update)}. Please wait, this may take a while...")
                
                success = True
                for submodule_path in submodules_to_update:
                    cmd = ['git', 'submodule', 'update', '--init', '--recursive', submodule_path]
                    result = self.run_command_with_output(cmd, self.debug_output_enabled)
                    if not result:
                        print(f"Failed to update submodule: {submodule_path}")
                        success = False
                    else:
                        print(f"Successfully updated submodule: {submodule_path}")
            
            if success:
                print("Successfully updated submodules")
                return True
            else:
                print("Failed to update submodules")
                return False
        except Exception as e:
            print(f"Failed to update submodules: {e}")
            return False
    
    def create_env(self, env_name: str, system_site_packages: bool = True) -> bool:
        try:
            self.env_name = env_name
            self.system_site_packages = system_site_packages
            self.env_path = Path(env_name).resolve()

            cmd = f"python -m venv {self.env_path}"
            if self.system_site_packages:
                cmd += " --system-site-packages"
            
            print(f"Creating virtual environment: {self.env_name}")
            
            success = self.run_command_with_output(cmd, self.debug_output_enabled)
            
            if success:
                print(f"Virtual environment '{self.env_name}' created successfully")
                return True
            else:
                print(f"Failed to create virtual environment")
                return False
        except Exception as e:
            print(f"Error creating virtual environment: {e}")
            return False
    
    def get_fastest_mirror(self) -> str:
        china_mirrors = [
            "https://pypi.tuna.tsinghua.edu.cn/simple/",
            "https://mirrors.aliyun.com/pypi/simple/",
        ]
        
        global_mirrors = [
            "https://pypi.org/simple/",
            "https://pypi.python.org/simple/",
        ]
        
        china_times = []
        for mirror in china_mirrors:
            try:
                start = time.time()
                requests.head(mirror, timeout=5)
                end = time.time()
                china_times.append(end - start)
            except:
                china_times.append(float('inf'))
        
        global_times = []
        for mirror in global_mirrors:
            try:
                start = time.time()
                requests.head(mirror, timeout=5)
                end = time.time()
                global_times.append(end - start)
            except:
                global_times.append(float('inf'))
        
        fastest_china_time = min(china_times) if china_times else float('inf')
        fastest_global_time = min(global_times) if global_times else float('inf')
        
        print(f"Fastest domestic mirror response time: {fastest_china_time:.2f}s")
        print(f"Fastest global mirror response time: {fastest_global_time:.2f}s")
        
        if fastest_china_time < fastest_global_time:
            print("Using domestic mirror based on speed test")
            return china_mirrors[china_times.index(fastest_china_time)]
        else:
            print("Using global mirror based on speed test")
            return global_mirrors[global_times.index(fastest_global_time)]
    
    def install_requirements(self, requirements_file: Union[str, Path] = "requirements.txt", timeout: int = 300) -> bool:
        req_path = Path(requirements_file)
        if not req_path.exists():
            print(f"Requirements file '{requirements_file}' does not exist")
            return False

        pip_path = self.env_path / "bin" / "pip"
            
        if not pip_path.exists():
            print(f"Pip not found in virtual environment: {pip_path}")
            return False

        try:
            cmd = f"{pip_path} install -r {req_path} --timeout {timeout} --retries 3 --default-timeout {timeout}"
            
            fastest_mirror = self.get_fastest_mirror()
            cmd += f" -i {fastest_mirror}"
            print(f"Using mirror: {fastest_mirror}")
            
            #print(f"Installing packages from {requirements_file} (timeout={timeout}s)")
            #print(f"Command: {cmd}")
            
            success = self.run_command_with_output(cmd, self.debug_output_enabled)
            
            if success:
                print(f"Successfully installed packages from {requirements_file}")
                return True
            else:
                print(f"Failed to install requirements")
                print("Possible solutions:")
                print("- Check internet connection")
                print("- Try installing packages one by one")
                print("- Use a different PyPI mirror")
                return False
        except Exception as e:
            print(f"Error installing requirements: {e}")
            return False
    
    def install_rpi_ws281x(self, target_folder_path: str = None) -> bool:
        venv_path = Path(target_folder_path) if target_folder_path else self.env_path

        try:
            source_lib_dir = Path.cwd() / "libraries" / "rpi-ws281x-python"
            dest_lib_dir = venv_path / "rpi-ws281x-python"
            
            if not source_lib_dir.exists():
                print(f"Error: Source library directory does not exist: {source_lib_dir}")
                return False
                
            if dest_lib_dir.exists():
                shutil.rmtree(dest_lib_dir) 
            shutil.copytree(source_lib_dir, dest_lib_dir)
            
            install_dir = dest_lib_dir / "library"
            if not install_dir.exists():
                print(f"Error: Library directory does not exist: {install_dir}")
                return False
            python_executable = venv_path / "bin" / "python" if os.name != 'nt' else venv_path / "Scripts" / "python.exe"
            if not python_executable.exists():
                print(f"Error: Cannot find Python executable in virtual environment: {python_executable}")
                return False
            install_cmd = f"cd {install_dir} && sudo {python_executable} setup.py install"
            #print(f"Running installation command in {install_dir}: {install_cmd}")
            success = self.run_command_with_output(install_cmd, self.debug_output_enabled)
            
            if success:
                print("rpi-ws281x-python installed successfully")
                return True
            else:
                print(f"rpi-ws281x-python installation failed")
                return False
        except Exception as e:
            print(f"Error during rpi-ws281x-python installation: {e}")
            return False
    
    def install_mpu6050(self, target_folder_path: str = None) -> bool:
        venv_path = Path(target_folder_path) if target_folder_path else self.env_path

        try:
            source_lib_dir = Path.cwd() / "libraries" / "mpu6050"
            dest_lib_dir = venv_path / "mpu6050"
            
            if not source_lib_dir.exists():
                print(f"Error: Source library directory does not exist: {source_lib_dir}")
                return False
            if dest_lib_dir.exists():
                shutil.rmtree(dest_lib_dir) 
            shutil.copytree(source_lib_dir, dest_lib_dir)
            
            install_dir = dest_lib_dir
            if not install_dir.exists():
                print(f"Error: Cannot find installation directory {install_dir}")
                return False
                
            python_executable = venv_path / "bin" / "python" if os.name != 'nt' else venv_path / "Scripts" / "python.exe"
            if not python_executable.exists():
                print(f"Error: Cannot find Python executable in virtual environment: {python_executable}")
                return False
                
            install_cmd = f"cd {install_dir} && sudo {python_executable} setup.py install"
            #print(f"Running installation command in {install_dir}: {install_cmd}")
            success = self.run_command_with_output(install_cmd, self.debug_output_enabled)
            
            if success:
                print("mpu6050 installed successfully")
                return True
            else:
                print(f"mpu6050 installation failed")
                return False
        except Exception as e:
            print(f"Error during mpu6050 installation: {e}")
            return False
    
    def install_utils_dependencies(self) -> bool:
        dependencies = [
            "build-essential",
            "cmake", 
            "device-tree-compiler",
            "libfdt-dev",
            "libgnutls28-dev",
            "libpio-dev"
        ]
        
        all_success = True
        
        for dep in dependencies:
            cmd = f"sudo apt install -y {dep}"
            success = self.run_command_with_output(cmd, self.debug_output_enabled)
            if success is False:
                print(f"✗ Failed to install {dep}")
                all_success = False
        
        if all_success:
            return True
        else:
            return False
    
    def install_utils(self, target_folder_path: str = None) -> bool:
        venv_path = Path(target_folder_path) if target_folder_path else self.env_path

        try:
            source_lib_dir = Path.cwd() / "libraries" / "utils"
            dest_lib_dir = venv_path / "utils"
            
            if not source_lib_dir.exists():
                print(f"Error: Source library directory does not exist: {source_lib_dir}")
                return False
                
            if dest_lib_dir.exists():
                shutil.rmtree(dest_lib_dir) 
            shutil.copytree(source_lib_dir, dest_lib_dir)

            if not self.install_utils_dependencies():
                print("Failed to install system dependencies, utils installation aborted")
                return False

            install_dir = dest_lib_dir / "piolib" / "examples"
            if not install_dir.exists():
                print(f"Error: Cannot find 'examples' directory at {install_dir}")
                return False
            cmake_cmd = f"cd {install_dir} && cmake -S . -B build"
            if not self.run_command_with_output(cmake_cmd, self.debug_output_enabled):
                print(f"CMake configuration failed")
                return False
            
            build_dir = install_dir / "build"
            make_cmd = f"cd {build_dir} && sudo make install"
            #print(f"Running make install: {make_cmd}")
            success = self.run_command_with_output(make_cmd, self.debug_output_enabled)
            
            if success:
                print("utils installed successfully")
                return True
            else:
                print(f"utils installation failed")
                return False
        except Exception as e:
            print(f"Error during utils installation: {e}")
            return False
    
    def install_luma_oled(self) -> bool:
        try:
            cmd = "sudo apt-get install -y python3-luma.oled"
            if not self.run_command_with_output(cmd, self.debug_output_enabled):
                print("Failed to install luma.oled, installation aborted")
                return False
            else:
                print("luma.oled installed successfully")
                return True
        except Exception as e:
            print(f"Error during luma.oled installation: {e}")
            return False
    
    def backup_config_txt(self, backup_dir: str = None) -> bool:
        try:
            source_file = Path("/boot/firmware/config.txt")
            if not source_file.exists():
                print(f"Error: Source file {source_file} does not exist")
                return False

            if backup_dir is None:
                backup_dir = Path("/boot/firmware/config_backups")
                backup_dir.mkdir(parents=True, exist_ok=True)
            else:
                backup_dir = Path(backup_dir)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"config.txt.{timestamp}.bak"
            
            shutil.copy2(source_file, backup_file)
            
            print(f"Successfully backed up {source_file} to {backup_file}")
            return True
            
        except PermissionError:
            print(f"Error: Permission denied when trying to backup {source_file}")
            return False
        except Exception as e:
            print(f"Error during config.txt backup: {e}")
            return False
    
    def find_and_update_line(self, search_prefix: str, new_line: str):
        try:
            file_path = '/boot/firmware/config.txt'
            with open(file_path, 'r') as f:
                lines = f.readlines()
            updated = False
            new_content = []
            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith(search_prefix) or stripped_line.startswith(f'#{search_prefix}'):
                    new_content.append(new_line + '\n')
                    updated = True
                else:
                    new_content.append(line)
            if not updated:
                new_content.append('\n' + new_line + '\n')
            with open(file_path, 'w') as f:
                f.writelines(new_content)
            return True
        except Exception as e:
            print(f"Failed to update file: {e}")
            return False
    
    def update_spi_function(self, enable: bool = True):
        spi_value = 'on' if enable else 'off'
        new_line = f'dtparam=spi={spi_value}'
        search_prefix = 'dtparam=spi'
        success = self.find_and_update_line(search_prefix, new_line)
        if success:
            print(f"SPI function has been set to: {spi_value}")
        else:
            print("Failed to update SPI function")
    
    def update_i2c_function(self, enable: bool = True):
        i2c_value = 'on' if enable else 'off'
        new_line = f'dtparam=i2c_arm={i2c_value}'
        search_prefix = 'dtparam=i2c_arm'
        success = self.find_and_update_line(search_prefix, new_line)
        if success:
            print(f"I2C function has been set to: {i2c_value}")
        else:
            print("Failed to update I2C function")
    
    def update_audio_function(self, enable: bool = False):
        audio_value = 'on' if enable else 'off'
        new_line = f'dtparam=audio={audio_value}'
        search_prefix = 'dtparam=audio'
        
        success = self.find_and_update_line(search_prefix, new_line)
        if success:
            print(f"Audio function has been set to: {audio_value}")
        else:
            print("Failed to update audio function")
    
    def update_camera_auto_detect(self, enable: bool = False):
        detect_value = '1' if enable else '0'
        new_line = f'camera_auto_detect={detect_value}'
        search_prefix = 'camera_auto_detect'
        
        success = self.find_and_update_line(search_prefix, new_line)
        if success:
            print(f"Camera auto-detect function has been set to: {detect_value}")
        else:
            print("Failed to update camera auto-detect function")
    
    def update_camera_config(self, camera_type: str = 'ov5647', camera_port: str = None):
        try:
            file_path = '/boot/firmware/config.txt'
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            new_content = []
            for line in lines:
                stripped_line = line.strip()
                if ('dtoverlay=ov5647' in stripped_line or 
                    'dtoverlay=imx219' in stripped_line or
                    stripped_line.startswith('#dtoverlay=ov5647') or
                    stripped_line.startswith('#dtoverlay=imx219')):
                    continue
                new_content.append(line)
            if camera_port:
                new_line = f'dtoverlay={camera_type},{camera_port}'
            else:
                new_line = f'dtoverlay={camera_type}'
            
            new_content.append('\n' + new_line + '\n')
            
            with open(file_path, 'w') as f:
                f.writelines(new_content)
            
            print(f"Camera configuration has been set to: {new_line}")
        except Exception as e:
            print(f"Failed to update camera configuration: {e}")
    
    def update_hardward_pwm_config(self, use_extended_config: bool = False):
        file_path = '/boot/firmware/config.txt'
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Failed to read file: {e}")
            return False
        
        new_content = []
        for line in lines:
            stripped_line = line.strip()
            if (stripped_line.startswith('dtoverlay=pwm-2chan') or 
                stripped_line.startswith('#dtoverlay=pwm-2chan')):
                continue
            new_content.append(line)
        
        if use_extended_config:
            pwm_config = "dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4"
        else:
            pwm_config = "dtoverlay=pwm-2chan"
        
        new_content.append('\n' + pwm_config)
        
        try:
            with open(file_path, 'w') as f:
                f.writelines(new_content)
            print(f"PWM configuration has been updated to: {pwm_config}")
            return True
        except Exception as e:
            print(f"Failed to write file: {e}")
            return False
    
    def select_kit_and_configure(self):
        """
        Let the user choose the kit and configure accordingly
        """
        kits = {
            '1': {'code': 'FNK0036', 'name': 'Freenove_Robot_Arm_Kit_for_Raspberry_Pi'},
            '2': {'code': 'FNK0043', 'name': 'Freenove_4WD_Smart_Car_Kit_for_Raspberry_Pi'},
            '3': {'code': 'FNK0050', 'name': 'Freenove_Robot_Dog_Kit_for_Raspberry_Pi'},
            '4': {'code': 'FNK0052', 'name': 'Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi'},
            '5': {'code': 'FNK0077', 'name': 'Freenove_Tank_Robot_Kit_for_Raspberry_Pi'},
            '6': {'code': 'FNK0100', 'name': 'Freenove_Computer_Case_Kit_for_Raspberry_Pi'},
            '7': {'code': 'FNK0107', 'name': 'Freenove_Computer_Case_Kit_Pro_for_Raspberry_Pi'},
            '8': {'code': 'FNK0108', 'name': 'Freenove_Computer_Case_Kit_Mini_for_Raspberry_Pi'},
            '9': {'code': 'FNK0113', 'name': 'Freenove_Tower_Cooler_for_Raspberry_Pi'}
        }
        
        print("Please select your kit:")
        for key, value in kits.items():
            print(f"{key}: {value['code']} - {value['name']}")
        
        selected_kit_code = None
        while True:
            choice = input("Enter kit number (1-8): ").strip()
            if choice in kits:
                selected_kit_code = kits[choice]['code']
                selected_kit_name = kits[choice]['name']
                print(f"Your selected kit is: {kits[choice]['code']} - {kits[choice]['name']}")
                break
            else:
                print("Invalid choice, please re-enter (1-8)")
        
        # Specific kits require connector version selection
        connector_version = None
        if selected_kit_code in ['FNK0043', 'FNK0050', 'FNK0052']:
            print("\nYour kit requires selecting connector version:")
            print("1: Connect_PCB_V1.0")
            print("2: Connect_PCB_V2.0")
            
            connector_choice = ""
            while connector_choice not in ['1', '2']:
                connector_choice = input("Please select connector version (1 or 2): ").strip()
                if connector_choice == '1':
                    connector_version = "Connect_PCB_V1.0"
                elif connector_choice == '2':
                    connector_version = "Connect_PCB_V2.0"
                else:
                    print("Invalid choice, please re-enter")
            
            print(f"Your selected connector version is: {connector_version}")
        
        # FNK0077 needs to ask for board version
        board_version = None
        if selected_kit_code == 'FNK0077':
            print("\nYour kit requires selecting board version:")
            print("1: FNK0077_V1.0")
            print("2: FNK0077_V2.0")
            
            board_choice = ""
            while board_choice not in ['1', '2']:
                board_choice = input("Please select board version (1 or 2): ").strip()
                if board_choice == '1':
                    board_version = "FNK0077_V1.0"
                elif board_choice == '2':
                    board_version = "FNK0077_V2.0"
                else:
                    print("Invalid choice, please re-enter")
            
            print(f"Your selected board version is: {board_version}")
        
        # Ask if camera configuration is needed
        print("\nDo you need to configure the camera?")
        print("1: Yes")
        print("2: No")
        
        camera_setup_needed = ""
        camera_version = None
        camera_port = None
        
        while camera_setup_needed not in ['1', '2']:
            camera_setup_needed = input("Please select (1 or 2): ").strip()
            if camera_setup_needed == '2':
                print("Skipping camera configuration")
                # Even if skipping camera configuration, record basic configuration info
                break
            elif camera_setup_needed == '1':
                # Camera version selection
                print("\nPlease select camera version:")
                print("1: ov5647")
                print("2: imx219")
                
                camera_choice = ""
                while camera_choice not in ['1', '2']:
                    camera_choice = input("Please select camera version (1 or 2): ").strip()
                    if camera_choice == '1':
                        camera_version = "ov5647"
                    elif camera_choice == '2':
                        camera_version = "imx219"
                    else:
                        print("Invalid choice, please re-enter")
                
                print(f"Your selected camera version is: {camera_version}")
                
                # If it's Raspberry Pi 5, ask for camera port
                pi_version = self.get_raspberry_pi_version()
                if pi_version == 5:
                    print(f"\nDetected that you are using Raspberry Pi {pi_version}, please select the port where the camera is connected:")
                    print("1: cam0")
                    print("2: cam1")
                    
                    port_choice = ""
                    while port_choice not in ['1', '2']:
                        port_choice = input("Please select camera port (1 or 2): ").strip()
                        if port_choice == '1':
                            camera_port = "cam0"
                        elif port_choice == '2':
                            camera_port = "cam1"
                        else:
                            print("Invalid choice, please re-enter")
                    
                    print(f"Your selected camera port is: {camera_port}")
                else:
                    # For non-Raspberry Pi 5, default to cam0
                    camera_port = "cam0"
                break
            else:
                print("Invalid choice, please re-enter")
        
        # Return complete configuration info, even if camera configuration was skipped
        print(f"\nConfiguration summary:")
        print(f"- Kit: {selected_kit_code}")
        if selected_kit_code in ['FNK0043', 'FNK0050', 'FNK0052']:
            print(f"- Connector version: {connector_version}")
        if selected_kit_code == 'FNK0077':
            print(f"- Board version: {board_version}")
        if camera_version and camera_port:
            print(f"- Camera version: {camera_version}")
            print(f"- Camera port: {camera_port}")
        else:
            print("- Camera: Not configured")
        
        return {
            'kit_code': selected_kit_code,
            'connector_version': connector_version if selected_kit_code in ['FNK0043', 'FNK0050', 'FNK0052'] else None,
            'board_version': board_version if selected_kit_code == 'FNK0077' else None,
            'camera_version': camera_version,
            'camera_port': camera_port,
            'kit_name': selected_kit_name
        }

    def install_kit_environment(self):
        system_platform = self.detect_platform()
        if system_platform == 'windows':
            pass
        elif system_platform == 'linux':
            pass
        elif system_platform == 'macos':
            pass
        elif system_platform == 'raspberry_pi':
            print("Installing kit environment for Raspberry Pi...")
            # Prompt user input, get user input information and extract to self.config
            try:
                self.config = self.select_kit_and_configure() 
                self.kit_code = self.config['kit_code']                   # Get user input kit code
                self.connector_version = self.config['connector_version'] # Get user input connector version
                self.board_version = self.config['board_version']         # Get user input board version
                self.camera_version = self.config['camera_version']       # Get user input camera version
                self.camera_port = self.config['camera_port']             # Get user input camera port
                self.kit_name = self.config['kit_name']
            except Exception as e:
                print(f"Error getting user input: {e}")

            # Backup config.txt file
            try:
                self.backup_config_txt()
            except Exception as e:
                print(f"Error running command: {e}")

            # try:
            #     self.update_submodules([self.kit_name])
            # except Exception as e:
            #     print(f"Error running command: {e}")

            # try:
            #     self.run_command_with_output(f"cp -r codes/{self.kit_name} .")
            # except Exception as e:
            #     print(f"Error running command: {e}")

            # Create virtual environment
            try:
                self.create_env(self.kit_code)
            except Exception as e:
                print(f"Error running command: {e}")

            # Install required dependencies
            try:
                self.install_requirements()
            except Exception as e:
                print(f"Error running command: {e}")
       
            # Install specified kit libraries
            if self.kit_code == "FNK0036": 
                if self.get_raspberry_pi_version() == 5:
                    if self.camera_version and self.camera_port:
                        self.update_camera_config(self.camera_version, self.camera_port)
                else:
                    if self.camera_version:
                        self.update_camera_config(self.camera_version)
                    if self.get_raspberry_pi_version() == 3:
                        self.update_audio_function(False)
                
                if self.get_raspberry_pi_version() == 5:
                    try:
                        self.update_spi_function(False)
                        self.update_submodules(['utils'])
                        self.install_utils()
                    except Exception as e:
                        print(f"Error running command: {e}")
                else:
                    try:
                        self.update_submodules(['rpi-ws281x-python'])
                        self.install_rpi_ws281x()
                    except Exception as e:
                        print(f"Error running command: {e}")

            elif self.kit_code == "FNK0043":
                self.update_i2c_function(True)
                if self.get_raspberry_pi_version() == 5:
                    if self.camera_version and self.camera_port:
                        self.update_camera_config(self.camera_version, self.camera_port)
                else:
                    if self.camera_version:
                        self.update_camera_config(self.camera_version)
                    if self.get_raspberry_pi_version() == 3:
                        self.update_audio_function(False)
                if self.connector_version == "V1.0":
                    self.update_spi_function(False)
                else:
                    self.update_spi_function(True)

                try:
                    self.update_submodules(['rpi-ws281x-python'])
                    self.install_rpi_ws281x()
                except Exception as e:
                    print(f"Error running command: {e}")
                    
            elif self.kit_code == "FNK0050" or self.kit_code == "FNK0052":
                self.update_i2c_function(True)
                if self.get_raspberry_pi_version() == 5:
                    if self.camera_version and self.camera_port:
                        self.update_camera_config(self.camera_version, self.camera_port)
                else:
                    if self.camera_version:
                        self.update_camera_config(self.camera_version)
                    if self.get_raspberry_pi_version() == 3:
                        self.update_audio_function(False)
                if self.connector_version == "V1.0":
                    self.update_spi_function(False)
                else:
                    self.update_spi_function(True)

                if self.connector_version == "V1.0":
                    try:
                        self.update_submodules(['rpi-ws281x-python'])
                    except Exception as e:
                        print(f"Error running command: {e}")
                    self.install_rpi_ws281x()
                try:
                    self.update_submodules(['mpu6050'])
                except Exception as e:
                    print(f"Error running command: {e}") 
                self.install_mpu6050()

            elif self.kit_code == "FNK0077":
                if self.get_raspberry_pi_version() == 5:
                    if self.camera_version and self.camera_port:
                        self.update_camera_config(self.camera_version, self.camera_port)
                else:
                    if self.camera_version:
                        self.update_camera_config(self.camera_version)
                if self.board_version == "V1.0":
                    self.update_spi_function(False)
                    self.update_hardward_pwm_config(False)
                    if self.get_raspberry_pi_version() == 3:
                        self.update_audio_function(False)
                else:
                    self.update_spi_function(True)
                    self.update_hardward_pwm_config(True)
                if self.board_version == "V1.0":
                    try:
                        self.update_submodules(['rpi-ws281x-python'])
                    except Exception as e:
                        print(f"Error running command: {e}")
                    self.install_rpi_ws281x()

            elif self.kit_code == "FNK0100" or self.kit_code == "FNK0107":
                self.update_i2c_function(True)
                self.install_luma_oled()
            elif self.kit_code == "FNK0108":
                try:
                    self.update_submodules(['utils'])
                except Exception as e:
                    print(f"Error running command: {e}")
                self.install_utils()
            elif self.kit_code == "FNK0113":
                self.update_i2c_function(True)
                try:
                    self.update_submodules(['utils'])
                except Exception as e:
                    print(f"Error running command: {e}")
                self.install_utils()
                self.install_luma_oled()
            else:
                print("Invalid kit code")
        elif system_platform == 'unknown':
            print("Unknown system platform")



if __name__ == "__main__":
    installer = LibraryInstaller()
    installer.install_kit_environment()
    