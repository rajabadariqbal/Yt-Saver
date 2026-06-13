[app]

# App info
title = YTSaver
package.name = ytsaver
package.domain = personal.pk

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

# Requirements - yt-dlp + kivy for Android
requirements = python3,kivy==2.3.0,yt-dlp,certifi,urllib3,requests,ffpyplayer

# Android permissions
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Old Android support - minimum API 21 = Android 5.0 (Lollipop)
android.minapi = 21
android.api = 33
android.ndk = 25b
android.sdk = 33

# Architecture - ARM for most Android phones
android.archs = arm64-v8a, armeabi-v7a

# Orientation
orientation = portrait

# Icons (optional - aap apni image rakh sakte ho)
# icon.filename = %(source.dir)s/assets/icon.png

# Fullscreen off - status bar dikhay
fullscreen = 0

[buildozer]

# Build directory
build_dir = ./.buildozer
bin_dir = ./bin

# Log level: 0=error, 1=info, 2=debug
log_level = 1

# Automatic accept Android SDK license
android.accept_sdk_license = True
