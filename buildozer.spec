
[app]

title = مدير كرة القدم
package.name = footballmanagertext
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,db,ttf
source.exclude_dirs = .git,.buildozer,bin,__pycache__

version = 1.0.0

requirements = python3==3.12.10,hostpython3==3.12.10,kivy==2.3.1

orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 26
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.branch = master

[buildozer]

log_level = 2
warn_on_root = 1
