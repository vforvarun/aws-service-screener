#!/bin/bash

# AWS Service Screener Installation Script
# This script installs AWS Service Screener in AWS CloudShell or any Linux environment
# Run this script from anywhere - it will download and set up everything automatically

set -e  # Exit on any error

echo "🚀 Installing AWS Service Screener..."
echo "======================================"

# Create installation directory
INSTALL_DIR="/tmp/aws-service-screener"
echo "📁 Setting up installation directory: $INSTALL_DIR"

# Navigate to /tmp
cd /tmp

# Create Python virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv .

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
python3 -m pip install --upgrade pip

# Remove existing installation if it exists
if [ -d "aws-service-screener" ]; then
    echo "🧹 Removing existing installation..."
    rm -rf aws-service-screener
fi

# Clone the repository
echo "📥 Cloning AWS Service Screener repository..."
git clone https://github.com/vforvarun/aws-service-screener.git

# Navigate to the cloned directory
cd aws-service-screener

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Run the unzip script for botocore lambda runtime
echo "📦 Setting up botocore lambda runtime..."
python3 unzip_botocore_lambda_runtime.py

# Create alias for easy usage
echo "🔗 Setting up screener command..."
SCREENER_PATH="$(pwd)/main.py"

# Add alias to bashrc for future sessions
echo "alias screener='python3 $SCREENER_PATH'" >> ~/.bashrc

# Create a direct executable script as an alternative
echo "#!/bin/bash" > /usr/local/bin/screener 2>/dev/null || echo "#!/bin/bash" > ~/screener
echo "cd $(pwd)" >> /usr/local/bin/screener 2>/dev/null || echo "cd $(pwd)" >> ~/screener
echo "python3 main.py \"\$@\"" >> /usr/local/bin/screener 2>/dev/null || echo "python3 main.py \"\$@\"" >> ~/screener

# Make it executable
chmod +x /usr/local/bin/screener 2>/dev/null || chmod +x ~/screener

# Check which method worked
if [ -x "/usr/local/bin/screener" ]; then
    SCREENER_CMD="screener"
    echo "✅ Created system-wide screener command"
elif [ -x "$HOME/screener" ]; then
    SCREENER_CMD="~/screener"
    echo "✅ Created screener command in home directory"
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME:"* ]]; then
        echo "export PATH=\"\$HOME:\$PATH\"" >> ~/.bashrc
    fi
else
    SCREENER_CMD="python3 $SCREENER_PATH"
    echo "⚠️  Using direct python command (alias will be available after restart)"
fi

echo ""
echo "✅ Installation completed successfully!"
echo "======================================"
echo ""
echo "📋 Usage Instructions:"
echo "----------------------"
echo "You can now run AWS Service Screener using:"
echo ""
echo "Method 1 (Recommended): $SCREENER_CMD"
echo "Method 2 (Direct): python3 $SCREENER_PATH"
echo "Method 3 (After restart): screener (alias will be available)"
echo ""
echo "Examples:"
echo ""
echo "1. Run in Singapore region with all services (recommended):"
echo "   $SCREENER_CMD --regions ap-southeast-1 --beta 1"
echo ""
echo "2. Run in Singapore region, stable releases only:"
echo "   $SCREENER_CMD --regions ap-southeast-1"
echo ""
echo "3. Run specific services (e.g., S3 only):"
echo "   $SCREENER_CMD --regions ap-southeast-1 --services s3"
echo ""
echo "4. Run in multiple regions:"
echo "   $SCREENER_CMD --regions ap-southeast-1,us-east-1"
echo ""
echo "5. Run in all regions:"
echo "   $SCREENER_CMD --regions ALL"
echo ""
echo "6. Run with Well-Architected Tool integration:"
echo "   $SCREENER_CMD --regions ap-southeast-1 --beta 1 --others '{\"WA\": {\"region\": \"ap-southeast-1\", \"reportName\": \"SS_Report\", \"newMileStone\": 1}}'"
echo ""
echo "📁 Output: Reports will be generated as output.zip"
echo ""
echo "🌐 IMPORTANT - Viewing Reports in AWS CloudShell:"
echo "================================================="
echo "AWS CloudShell doesn't allow external access to localhost ports, so you have 2 options:"
echo ""
echo "Option 1 (Recommended): Download and use standalone server"
echo "   • The tool generates output.zip with a built-in web server script"
echo "   • Download using CloudShell's 'Actions > Download file' menu"
echo "   • Extract the zip file on your local machine"
echo "   • Run: python3 start_report_server.py"
echo "   • This automatically starts a web server and opens your browser"
echo ""
echo "Option 2: Use the built-in web server (CloudShell terminal only)"
echo "   • The tool automatically starts a web server after generating reports"
echo "   • You can view the report URL in the CloudShell terminal"
echo "   • This only works within the CloudShell environment"
echo "   • To disable web server: add --no_webserver flag"
echo ""
echo "💡 Tip: The web server will keep running until you press Ctrl+C"
echo ""
echo "🔄 To use the 'screener' alias in new terminal sessions:"
echo "   source ~/.bashrc  OR  restart your terminal"
echo ""
echo "📖 For more information, see the README.md file"