from __future__ import absolute_import, division, print_function

import setuptools

with open('README.rst') as readme_file:
  readme = readme_file.read()

setuptools.setup(
      name='fast_dp',
      description='Fast DP: Fast Data Processsing with XDS',
      long_description=readme,
      long_description_content_type='text/x-rst',
      author='Diamond Light Source',
      author_email='scientificsoftware@diamond.ac.uk',

      version='1.0.1',

      url='https://github.com/DiamondLightSource/fast_dp',
      download_url="https://github.com/DiamondLightSource/fast_dp/releases",
      license='Apache-2.0',

      install_requires=[],
      packages=['fast_dp'],
      package_data={'fast_dp': ['templates/*.INP', 'templates/ispyb.xml']},

      entry_points={
        'libtbx.dispatcher.script': [
          'fast_dp=fast_dp',
          'fast_rdp=fast_rdp',
          'header2edna_xml=header2edna_xml',
        ],
      },
      scripts=[
        'bin/fast_dp',
        'bin/fast_rdp',
        'bin/header2edna_xml',
      ],

      tests_require=['mock', 'procrunner', 'pytest'],
      classifiers = [
        'Development Status :: 5 - Production/Stable',
#       'License :: OSI Approved :: Apache Software License 2.0 (Apache-2.0)', # eventually. https://github.com/pypa/warehouse/issues/2996
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Operating System :: POSIX :: Linux',
      ],
)
