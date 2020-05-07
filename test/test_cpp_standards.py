import os

import jinja2
import pytest

from . import utils
from .template_projects import TemplateProject

cpp_template_project = TemplateProject()

cpp_template_project.files['setup.py'] = jinja2.Template(r'''
from setuptools import Extension, setup

import platform
import sys
if platform.system() == 'Windows' and sys.version_info >= (3,5,0):
    import sys
    print(sys.path)
    print(setuptools.__file__, setuptools.__version__)

    import distutils._msvccompiler
    import distutils.util

    print(distutils._msvccompiler._get_vc_env, distutils._msvccompiler._get_vc_env.__module__)
    print(setuptools.msvc.msvc14_get_vc_env('x64' if 'amd64' in distutils.util.get_platform() else 'x86')['path'])

    compiler = distutils._msvccompiler.MSVCCompiler()
    print(compiler)
    compiler.initialize()
    print(compiler.cc)


setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.cpp'], language="c++", extra_compile_args={{ extra_compile_args }})],
    version="0.1.0",
)
''')

cpp_template_project.files['spam.cpp'] = jinja2.Template(r'''
#include <Python.h>

{{ spam_cpp_top_level_add }}

static PyObject *
spam_system(PyObject *self, PyObject *args)
{
    const char *command;
    int sts;

    if (!PyArg_ParseTuple(args, "s", &command))
        return NULL;
    sts = system(command);
    return PyLong_FromLong(sts);
}

/* Module initialization */

#if PY_MAJOR_VERSION >= 3
    #define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
    #define MOD_DEF(m, name, doc, methods, module_state_size) \
        static struct PyModuleDef moduledef = { \
            PyModuleDef_HEAD_INIT, name, doc, module_state_size, methods, }; \
        m = PyModule_Create(&moduledef);
    #define MOD_RETURN(m) return m;
#else
    #define MOD_INIT(name) PyMODINIT_FUNC init##name(void)
    #define MOD_DEF(m, name, doc, methods, module_state_size) \
        m = Py_InitModule3(name, methods, doc);
    #define MOD_RETURN(m) return;
#endif

static PyMethodDef module_methods[] = {
    {"system", (PyCFunction)spam_system, METH_VARARGS,
     "Execute a shell command."},
    {NULL}  /* Sentinel */
};

MOD_INIT(spam)
{
    PyObject* m;

    MOD_DEF(m,
            "spam",
            "Example module",
            module_methods,
            -1)

    MOD_RETURN(m)
}
''')


def test_cpp11(tmp_path):
    # This test checks that the C++11 standard is supported
    project_dir = tmp_path / 'project'

    project = cpp_template_project.copy()
    extra_compile_args = ['/std:c++11'] if utils.platform == 'windows' else ['-std=c++11']
    project.template_context['extra_compile_args'] = extra_compile_args
    project.template_context['spam_cpp_top_level_add'] = '#include <array>'
    project.generate(project_dir)

    # VC++ for Python 2.7 does not support modern standards
    add_env = {'CIBW_SKIP': 'cp27-win* pp27-win32'}

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if 'cp27-cp27m-win' not in w and 'pp27-pypy_73-win32' not in w]

    assert set(actual_wheels) == set(expected_wheels)


def test_cpp14(tmp_path):
    # This test checks that the C++14 standard is supported
    project_dir = tmp_path / 'project'

    project = cpp_template_project.copy()
    extra_compile_args = ['/std:c++14'] if utils.platform == 'windows' else ['-std=c++14']
    project.template_context['extra_compile_args'] = extra_compile_args
    project.template_context['spam_cpp_top_level_add'] = "int a = 100'000;"
    project.generate(project_dir)

    # VC++ for Python 2.7 does not support modern standards
    # The manylinux1 docker image does not have a compiler which supports C++11
    add_env = {'CIBW_SKIP': 'cp27-win* pp27-win32'}

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if 'cp27-cp27m-win' not in w
                       and 'pp27-pypy_73-win32' not in w]

    assert set(actual_wheels) == set(expected_wheels)


cpp17_project = cpp_template_project.copy()

if utils.platform == 'windows':
    cpp17_project.template_context['extra_compile_args'] = ['/std:c++17', '/wd5033']
else:
    cpp17_project.template_context['extra_compile_args'] = ['-std=c++17', '-Wno-register']

cpp17_project.template_context['spam_cpp_top_level_add'] = r'''
#include <utility>
auto a = std::pair(5.0, false);
'''


def test_cpp17(tmp_path):
    # This test checks that the C++17 standard is supported
    project_dir = tmp_path / 'project'

    cpp17_project.generate(project_dir)

    # Python and PyPy 2.7 use the `register` keyword which is forbidden in the C++17 standard
    # The manylinux1 docker image does not have a compiler which supports C++11
    if os.environ.get('APPVEYOR_BUILD_WORKER_IMAGE', '') == 'Visual Studio 2015':
        pytest.skip('Visual Studio 2015 does not support C++17')

    add_env = {'CIBW_SKIP': 'cp27-win* pp27-win32'}

    if utils.platform == 'macos':
        add_env['MACOSX_DEPLOYMENT_TARGET'] = '10.13'

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0', macosx_deployment_target='10.13')
                       if 'cp27-cp27m-win' not in w
                       and 'pp27-pypy_73-win32' not in w]

    assert set(actual_wheels) == set(expected_wheels)


def test_cpp17_py27_modern_msvc_workaround(tmp_path):
    # This test checks the workaround for building Python 2.7 wheel with MSVC 14

    if utils.platform != 'windows':
        pytest.skip('the test is only relevant to the Windows build')

    if os.environ.get('APPVEYOR_BUILD_WORKER_IMAGE', '') == 'Visual Studio 2015':
        pytest.skip('Visual Studio 2015 does not support C++17')

    project_dir = tmp_path / 'project'
    cpp17_project.generate(project_dir)

    # VC++ for Python 2.7 (i.e., MSVC 9) does not support modern standards
    # This is a workaround which forces distutils/setupstools to a newer version
    # Wheels compiled need a more modern C++ redistributable installed, which is not
    # included with Python: see documentation for more info
    # DISTUTILS_USE_SDK and MSSdk=1 tell distutils/setuptools that we are adding
    # MSVC's compiler, tools, and libraries to PATH ourselves
    add_env = {'DISTUTILS_USE_SDK': '1', 'MSSdk': '1'}

    # Use existing setuptools code to run Visual Studio's vcvarsall.bat and get the
    # necessary environment variables, since running vcvarsall.bat in a subprocess
    # does not keep the relevant environment variables
    # There are different environment variables for 32-bit/64-bit targets, so we
    # need to run cibuildwheel twice, once for 32-bit with `vcvarsall.bat x86, and
    # once for 64-bit with `vcvarsall.bat x64`
    # In a normal CI setup, just run vcvarsall.bat before running cibuildwheel and set
    # DISTUTILS_USE_SDK and MSSdk
    import setuptools

    def add_vcvars(prev_env, platform):
        vcvarsall_env = setuptools.msvc.msvc14_get_vc_env(platform)
        env = prev_env.copy()
        for vcvar in ['path', 'include', 'lib']:
            env[vcvar] = vcvarsall_env[vcvar]
        return env

    add_env_x86 = add_vcvars(add_env, 'x86')
    add_env_x86['CIBW_BUILD'] = '?p27-win32'
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env_x86)

    add_env_x64 = add_vcvars(add_env, 'x64')
    add_env_x64['CIBW_BUILD'] = 'cp27-win_amd64'
    actual_wheels += utils.cibuildwheel_run(project_dir, add_env=add_env_x64)

    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if 'cp27-cp27m-win' in w
                       or 'pp27-pypy_73-win32' in w]

    assert set(actual_wheels) == set(expected_wheels)
