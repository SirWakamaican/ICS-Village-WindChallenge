#!/bin/bash

ETHERCAT_INSTALL=""

if [ $# -eq 0 ]; then
    echo ""
    echo "Error: You must provide a platform name as argument"
    echo ""
    echo "Usage: ./install.sh [platform]   where [platform] can be"
    echo "  win           Install OpenPLC on Windows over Cygwin"
    echo "  linux         Install OpenPLC on a Debian-based Linux distribution"
    echo "  docker        Install OpenPLC in a Docker container"
    echo "  rpi           Install OpenPLC on a Raspberry Pi"
    echo "  neuron        Install OpenPLC on a UniPi Neuron PLC"
    echo "  custom        Skip all specific package installation and tries to install"
    echo "                OpenPLC assuming your system already has all dependencies met."
    echo "                This option can be useful if you're trying to install OpenPLC"
    echo "                on an unsuported Linux platform or had manually installed"
    echo "                all the dependency packages before."
    echo ""
    exit 1
fi

#set -x 
# arg1: sudo or blank
function linux_install_deps {
    #Detecting OS type
    INSTALLER=""
    OS=$(awk '/NAME=/' /etc/*-release | sed -n '1 p' | cut -d= -f2 | cut -d\" -f2 | cut -d" " -f1)

    if [ "$OS" = "Fedora" ]; then
        INSTALLER="yum"
    elif [ "$OS" = "CentOS" ]; then
        INSTALLER="yum"
    elif [ "$OS" = "Red" ]; then
        INSTALLER="yum"
    else
        INSTALLER="apt"
    fi
    
    if [ "$INSTALLER" = "yum" ]; then
        yum clean expire-cache
        yum check-update
        $1 yum -q -y install curl make automake gcc gcc-c++ kernel-devel pkg-config bison flex autoconf libtool openssl-devel cmake python3 python3-pip
        $1 yum -q -y install python2.7 python2-devel
    #Installing dependencies for Ubuntu/Mint/Debian
    else
        $1 apt-get update
        $1 apt-get install -y build-essential pkg-config bison flex autoconf \
                              automake libtool make git python2.7 \
                              sqlite3 cmake git curl python3 python3-pip
    fi
    curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
    $1 python2.7 get-pip.py
}

function install_py_deps {
    $1 pip2 install flask
    $1 pip2 install flask-login
    $1 pip2 install pyserial
    $1 pip2 install pymodbus
    $1 pip3 install pymodbus==2.5.3
}

function install_all_libs {
        echo ""
    echo "[MATIEC COMPILER]"
    cd utils/matiec_src
    autoreconf -i
    ./configure
    make
    cp ./iec2c ../../webserver/
    if [ $? -ne 0 ]; then
        echo "Error compiling MatIEC"
        echo "OpenPLC was NOT installed!"
        exit 1
    fi
    cd ../..

    echo ""
    echo "[ST OPTIMIZER]"
    cd utils/st_optimizer_src
    g++ st_optimizer.cpp -o st_optimizer
    cp ./st_optimizer ../../webserver/
    if [ $? -ne 0 ]; then
        echo "Error compiling ST Optimizer"
        echo "OpenPLC was NOT installed!"
        exit 1
    fi
    cd ../..

    echo ""
    echo "[GLUE GENERATOR]"
    cd utils/glue_generator_src
    g++ -std=c++11 glue_generator.cpp -o glue_generator
    cp ./glue_generator ../../webserver/core
    if [ $? -ne 0 ]; then
        echo "Error compiling Glue Generator"
        echo "OpenPLC was NOT installed!"
        exit 1
    fi
    cd ../..

    if [ "$ETHERCAT_INSTALL" == "install" ]; then
        echo ""
        echo "[EtherCAT]"
        cd utils/ethercat_src
        ./install.sh
        if [ $? -ne 0 ]; then
            echo "Error compiling EtherCAT"
            echo "OpenPLC was NOT installed!"
            exit 1
        fi
        cd ../..
    fi

    echo ""
    echo "[OPEN DNP3]"
    cd utils/dnp3_src
    echo "creating swapfile..."
    $1 dd if=/dev/zero of=swapfile bs=1M count=1000
    $1 mkswap swapfile
    $1 swapon swapfile
    cmake ../dnp3_src
    make
    $1 make install
    if [ $? -ne 0 ]; then
        echo "Error installing OpenDNP3"
        echo "OpenPLC was NOT installed!"
        exit 1
    fi
    $1 ldconfig
    echo "removing swapfile..."
    $1 swapoff swapfile
    $1 rm -f ./swapfile
    cd ../..

    echo ""
    echo "[LIBMODBUS]"
    cd utils/libmodbus_src
    ./autogen.sh
    ./configure
    $1 make install
    if [ $? -ne 0 ]; then
        echo "Error installing Libmodbus"
        echo "OpenPLC was NOT installed!"
        exit 1
    fi
    $1 ldconfig
    cd ../..

    if [ "$1" == "sudo" ]; then
        echo ""
        echo "[OPENPLC SERVICE]"
        WORKING_DIR=$(pwd)
        echo -e "[Unit]\n\
Description=OpenPLC Service\n\
After=network.target\n\
\n\
[Service]\n\
Type=simple\n\
Restart=always\n\
RestartSec=1\n\
User=root\n\
Group=root\n\
WorkingDirectory=$WORKING_DIR\n\
ExecStart=$WORKING_DIR/start_openplc.sh\n\
\n\
[Install]\n\
WantedBy=multi-user.target" >> openplc.service
        $1 cp -rf ./openplc.service /lib/systemd/system/
        rm -rf openplc.service
        echo "Enabling OpenPLC Service..."
        $1 systemctl daemon-reload
        $1 systemctl enable openplc
    fi
}

if [ "$1" == "win" ]; then
    echo "Installing OpenPLC on Windows"
    cp ./utils/apt-cyg/apt-cyg ./
    install apt-cyg /bin
    apt-cyg update
    apt-cyg install lynx
    
    echo "Installing Python 2.7"
    cd utils/python2
    tar -xf python27-2.7.18-4.tar.xz
    rsync -a ./etc/ /etc/
    rsync -a ./usr/ /usr/
    /etc/postinstall/python2.sh
    ln -s /usr/bin/python2.7.exe /usr/bin/python2
    cd ..
    cd ..
    
    # apt-cyg remove gcc-core gcc-g++ pkg-config automake autoconf libtool make python2 python2-pip sqlite3
    apt-cyg install gcc-core gcc-g++ git pkg-config automake autoconf libtool make sqlite3 python3
    lynx -source https://bootstrap.pypa.io/pip/2.7/get-pip.py > get-pip.py
    lynx -source https://bootstrap.pypa.io/pip/get-pip.py > get-pip3.py
    /usr/bin/python2 get-pip.py
    /usr/bin/python3 get-pip3.py
    /usr/bin/python2 -m pip install flask
    /usr/bin/python2 -m pip install flask-login
    /usr/bin/python2 -m pip install pyserial
    /usr/bin/python2 -m pip install pymodbus
    /usr/bin/python3 -m pip install pymodbus==2.5.3

    echo ""
    echo "[MATIEC COMPILER]"
    cp ./utils/matiec_src/bin_win32/*.* ./webserver/
    if [ $? -ne 0 ]; then
        echo "Error compiling MatIEC"
        echo "OpenPLC was NOT installed!"
        exit 1
    fi

    echo ""
    echo "[ST OPTIMIZER]"
    cd utils/st_optimizer_src
    g++ st_optimizer.cpp -o st_optimizer
    cp ./st_optimizer.exe ../../webserver/
    if [ $? -ne 0 ]; then
        echo "Error compiling ST Optimizer"
        echo "OpenPLC was NOT installed!"
        exit 1
    fi
    cd ../..

    echo ""
    echo "[GLUE GENERATOR]"
    cd utils/glue_generator_src
    g++ glue_generator.cpp -o glue_generator
    cp ./glue_generator.exe ../../webserver/core
    if [ $? -ne 0 ]; then
        echo "Error compiling Glue Generator"
        echo "OpenPLC was NOT installed!"
        exit 1
    fi
    cd ../..

    echo ""
    echo "[OPEN DNP3]"
    cd webserver/core
    if test -f dnp3.cpp; then
        mv dnp3.cpp dnp3.disabled
        if [ $? -ne 0 ]; then
            echo "Error disabling OpenDNP3"
            echo "OpenPLC was NOT installed!"
            exit 1
        fi
    fi
    if test -f dnp3_dummy.disabled; then
        mv dnp3_dummy.disabled dnp3_dummy.cpp
        if [ $? -ne 0 ]; then
            echo "Error disabling OpenDNP3"
            echo "OpenPLC was NOT installed!"
            exit 1
        fi
    fi
    cd ../..

    echo ""
    echo "[LIBMODBUS]"
    cd utils/libmodbus_src
    ./autogen.sh
    ./configure
    make install
    if [ $? -ne 0 ]; then
        echo "Error installing Libmodbus"
        echo "OpenPLC was NOT installed!"
        exit 1
    fi
    cd ../..

    echo ""
    echo "[FINALIZING]"
    cd webserver/scripts
    ./change_hardware_layer.sh blank
    ./compile_program.sh blank_program.st
    cp ./start_openplc.sh ../../


elif [ "$1" == "linux" ]; then

    echo "Installing OpenPLC on Linux"
    if [ "$2" == "ethercat" ]; then
        echo "including EtherCAT"
        ETHERCAT_INSTALL="install"
        echo ethercat > webserver/scripts/ethercat
    else
        echo "" > webserver/scripts/ethercat
    fi
    linux_install_deps sudo
    
    install_py_deps
    install_py_deps "sudo -H"

    install_all_libs sudo
    
    #Detecting OS type
    OS_TYPE=""
    OS=$(awk '/NAME=/' /etc/*-release | sed -n '1 p' | cut -d= -f2 | cut -d\" -f2 | cut -d" " -f1)

    if [ "$OS" = "Fedora" ]; then
        OS_TYPE="yum"
    elif [ "$OS" = "CentOS" ]; then
        OS_TYPE="yum"
    elif [ "$OS" = "Red" ]; then
        OS_TYPE="yum"
    else
        OS_TYPE="apt"
    fi
    
    #Fix for Fedora
    if [ "$OS_TYPE" = "yum" ]; then
        sudo cp /usr/local/lib/pkgconfig/libmodbus.pc /usr/share/pkgconfig/
        sudo cp /usr/local/lib/lib*.* /lib64/
    fi
    
    echo ""
    echo "[FINALIZING]"
    cd webserver/scripts
    ./change_hardware_layer.sh blank_linux
    ./compile_program.sh blank_program.st
    cp ./start_openplc.sh ../../


elif [ "$1" == "docker" ]; then
    echo "Installing OpenPLC on Linux inside Docker"
    linux_install_deps
    install_py_deps
    install_all_libs

    echo ""
    echo "[FINALIZING]"
    cd webserver/scripts
    ./change_hardware_layer.sh blank_linux
    ./compile_program.sh blank_program.st
    cp ./start_openplc.sh ../../

elif [ "$1" == "rpi" ]; then
    echo "Installing OpenPLC on Raspberry Pi"
    
    linux_install_deps sudo
    sudo apt-get install -y wiringpi

    install_py_deps
    install_py_deps "sudo -H" 

    install_all_libs sudo

    echo ""
    echo "[FINALIZING]"
    cd webserver/scripts
    ./change_hardware_layer.sh blank_linux
    ./compile_program.sh blank_program.st
    cp ./start_openplc.sh ../../



elif [ "$1" == "neuron" ]; then
    echo "Installing OpenPLC on UniPi Neuron PLC"
    
    echo ""
    echo "[DISABLING UNIPI SERVICES]"
    sudo systemctl stop neuronhost.service
    sudo systemctl disable neuronhost.service
    sudo systemctl stop neurontcp.service
    sudo systemctl disable neurontcp.service
    sudo systemctl stop evok.service
    sudo systemctl disable evok.service

    linux_install_deps sudo
    
    install_py_deps
    install_py_deps "sudo -H"

    install_all_libs sudo

    echo ""
    echo "[FINALIZING]"
    cd webserver/scripts
    ./change_hardware_layer.sh blank_linux
    ./compile_program.sh blank_program.st
    cp ./start_openplc.sh ../../



elif [ "$1" == "custom" ]; then
    echo "Installing OpenPLC on Custom Platform"

    install_all_libs

    echo ""
    echo "[FINALIZING]"
    cd webserver/scripts
    ./change_hardware_layer.sh blank_linux
    ./compile_program.sh blank_program.st
    cp ./start_openplc.sh ../../


else
    echo ""
    echo "Error: unrecognized platform"
    echo ""
    echo "Usage: ./install.sh [platform]   where [platform] can be"
    echo "  win           Install OpenPLC on Windows over Cygwin"
    echo "  linux         Install OpenPLC on a Debian-based Linux distribution"
    echo "  rpi           Install OpenPLC on a Raspberry Pi"
    echo "  custom        Skip all specific package installation and tries to install"
    echo "                OpenPLC assuming your system already has all dependencies met."
    echo "                This option can be useful if you're trying to install OpenPLC"
    echo "                on an unsuported Linux platform or had manually installed"
    echo "                all the dependency packages before."
    echo ""
    exit 1
fi
