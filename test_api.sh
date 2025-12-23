#!/bin/bash
BASE_URL="http://127.0.0.1:5000"
COOKIE_JAR="cookies.txt"

echo "1. Registering User..."
curl -s -X POST "$BASE_URL/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
echo -e "\n"

echo "2. Logging In..."
curl -s -c $COOKIE_JAR -X POST "$BASE_URL/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "password123"}'
echo -e "\n"

echo "3. Uploading Wallpaper..."
# Create a dummy file if not exists
if [ ! -f test_image.png ]; then
    convert -size 100x100 xc:white test_image.png
fi

curl -s -b $COOKIE_JAR -X POST "$BASE_URL/upload" \
     -F "file=@test_image.png" \
     -F "title=Test Wallpaper" \
     -F "tags=test, white, png"
echo -e "\n"

echo "4. Listing Wallpapers..."
curl -s "$BASE_URL/"
echo -e "\n"

echo "5. Searching Wallpapers..."
curl -s "$BASE_URL/search?q=white"
echo -e "\n"
