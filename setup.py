import setuptools


setuptools.setup(
    name='fx-library',
    description='FX related library with Pyrhon',
    version='4.0.0',
    author='mniyk',
    author_email='my.name.is.yohei.kono@gmail.com',
    url='https://github.com/mniyk/fx-library.git',
    packages=setuptools.find_packages(exclude=['tests']),
    install_requires=['MetaTrader5', 'pyti'])
