#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "======================================================================"
echo "  Telegram Session Creator for Docker Deployment"
echo "======================================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ ERROR: Docker is not installed${NC}"
    echo ""
    echo "Please install Docker first:"
    echo "  - macOS: https://docs.docker.com/desktop/install/mac-install/"
    echo "  - Linux: https://docs.docker.com/engine/install/"
    echo "  - Windows: https://docs.docker.com/desktop/install/windows-install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ ERROR: .env file not found${NC}"
    echo ""
    echo "Please create .env file with your credentials:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your Telegram API credentials"
    exit 1
fi

# Check if session already exists
if [ -f sessions/user.session ]; then
    echo -e "${YELLOW}⚠️  WARNING: Session file already exists${NC}"
    echo ""
    echo "File: sessions/user.session"
    echo ""
    read -p "Do you want to recreate it? This will log out the existing session. (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    echo ""
    echo "Removing old session..."
    rm -f sessions/user.session
    rm -f sessions/user.session-journal
fi

# Create sessions directory if it doesn't exist
mkdir -p sessions

echo -e "${BLUE}Building Docker image (this may take a minute)...${NC}"
docker-compose build telebrief

echo ""
echo -e "${GREEN}Starting interactive session creation...${NC}"
echo ""
echo "You will be prompted for:"
echo "  1. Your phone number (international format: +1234567890)"
echo "  2. Verification code (sent to your Telegram app)"
echo "  3. 2FA password (if you have it enabled)"
echo ""
echo "======================================================================"
echo ""

# Run Docker container interactively to create session
docker run --rm -it \
    --env-file .env \
    -v "$(pwd)/sessions:/app/sessions" \
    -v "$(pwd)/.env:/app/.env:ro" \
    telebrief:latest \
    python -c "
import asyncio
import os
import sys
from telethon import TelegramClient

async def create_session():
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')

    if not api_id or not api_hash:
        print('❌ ERROR: Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in .env file')
        sys.exit(1)

    client = TelegramClient('sessions/user', int(api_id), api_hash)

    try:
        await client.start()

        print()
        print('=' * 70)
        print('✅ SUCCESS! Session created successfully')
        print('=' * 70)
        print()

        me = await client.get_me()
        print(f'Authenticated as: {me.first_name}')
        if me.username:
            print(f'Username: @{me.username}')
        print(f'Phone: {me.phone}')
        print()
        print('Session file: sessions/user.session')
        print()
        print('Next steps:')
        print('  1. Run: docker-compose up -d')
        print('  2. Check logs: docker-compose logs -f telebrief')
        print()

    except KeyboardInterrupt:
        print()
        print('⚠️  Session creation cancelled')
        sys.exit(1)
    except Exception as e:
        print(f'❌ Error: {e}')
        sys.exit(1)
    finally:
        await client.disconnect()

asyncio.run(create_session())
"

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}======================================================================"
    echo "  Session file created successfully!"
    echo "======================================================================${NC}"
    echo ""
    echo "File location: $(pwd)/sessions/user.session"
    echo ""
    echo -e "${GREEN}✅ You can now run:${NC}"
    echo "     docker-compose up -d"
    echo ""
else
    echo ""
    echo -e "${RED}======================================================================"
    echo "  Session creation failed"
    echo "======================================================================${NC}"
    echo ""
    echo "Common issues:"
    echo "  - Wrong API credentials in .env"
    echo "  - Invalid phone number format (use +1234567890)"
    echo "  - Wrong verification code"
    echo ""
    echo "Try again: ./create_session.sh"
    echo ""
fi

exit $RESULT