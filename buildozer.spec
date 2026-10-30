
[app]

title = مدير كرة القدم
package.name = footballmanagertext
package.domain = com.karim
source.dir = .

source.include_exts = py,kv,png,jpg,jpeg,atlas,db,ttf
source.exclude_dirs = .git,.buildozer,bin,__pycache__

version = 1.0.0

requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.python_version = 3.10

[buildozer]
log_level = 2
warn_on_root = 1
 
