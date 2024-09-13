from setuptools import setup
from distutils.core import Extension
from Cython.Build import cythonize
import os
from sys import platform

if platform == 'darwin':    #macOs
    os.environ["CC"] = "clang"
    os.environ["CXX"] = "clang"
else:
    os.environ["CC"] = "g++"
    os.environ["CXX"] = "g++"
    extra_compile_args = ["-O3", "-march=native", "-std=c++17", "-pthread", "-Wall"]
    extra_link_args=[]

HOME = os.path.expanduser('~')
if platform == 'darwin':
    extra_compile_args += ['-lomp', '-I/usr/local/opt/libomp/include']
    extra_link_args += ['-lomp', '-L/usr/local/opt/libomp/include']
else:
    extra_compile_args += ['-fopenmp']
    extra_link_args += ['-fopenmp']



module_sparklyRG = Extension("wrapper",
                             sources=["wrapper.pyx"],
                             libraries=[],
                             include_dirs=['.'], 
                             language='c++',
                             extra_link_args=extra_link_args,
                             extra_compile_args=extra_compile_args)


setup(name='wrapper', ext_modules=cythonize([module_sparklyRG], language_level = "3"))
