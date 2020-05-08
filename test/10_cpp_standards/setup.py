import os
import platform

from setuptools import (
    Extension,
    setup,
)


from setuptools.command.build_ext import build_ext
class CustomBuild(build_ext):
    def build_extensions(self):
        print("self.compiler", self.compiler)
        build_ext.build_extensions(self)


import platform
import sys
if platform.system() == 'Windows' and sys.version_info >= (3,5,0):
    import sys
    print(sys.path)
    print(setuptools.__file__, setuptools.__version__)
    import distutils
    import distutils._msvccompiler
    import distutils.util
    print(distutils.__file__)
    print(distutils._msvccompiler.__file__)
    print(distutils.util.__file__)
    import distutils.ccompiler
    print(distutils.ccompiler.__file__, distutils.ccompiler.compiler_class)
    print(distutils._msvccompiler._get_vc_env, distutils._msvccompiler._get_vc_env.__module__)
    print(setuptools.msvc.msvc14_get_vc_env('x64' if 'amd64' in distutils.util.get_platform() else 'x86')['path'])
    compiler = distutils._msvccompiler.MSVCCompiler()
    print(compiler)
    compiler.initialize()
    print(compiler.cc)
    from setuptools.command.build_ext import _build_ext
    print(_build_ext)


standard = os.environ["STANDARD"]

language_standard = "/std:c++" + standard if platform.system() == "Windows" else "-std=c++" + standard

extra_compile_args = [language_standard, "-DSTANDARD=" + standard]

if standard == "17":
    if platform.system() == "Windows":
        extra_compile_args.append("/wd5033")
    else:
        extra_compile_args.append("-Wno-register")

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.cpp'], language="c++", extra_compile_args=extra_compile_args)],
    version="0.1.0",
    cmdclass=dict(build_ext=CustomBuild),
)
