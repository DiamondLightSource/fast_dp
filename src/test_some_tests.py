# Minimal intro "How to make a test":
#
# 1. Files matching pattern test_*.py contain tests.
# 2. Functions matching pattern test_* are tests.
#
# 3. To run the tests in a dials distribution, install dlstbx and run
#       py.test

# Advanced stuff:
# 4. To automatically run tests on file changes, run
#       ptw     # ("py.test watch")
# 5. Use asserts, generally no need to create or import other
#    assert implementations.
#    eg.
#
#       def test_assert():
#         assert [1,2,3] == [1,2,4]
#
#    will give you the following output:
#
#       def test_assert():
#   >    assert [1,2,3] == [1,2,4]
#   E    assert [1, 2, 3] == [1, 2, 4]
#   E      At index 2 diff: 3 != 4
#   E      Use -v to get the full diff
#
# 6. more advanced stuff at https://docs.pytest.org/en/latest/

import procrunner
import libtbx.load_env
import os
import pytest

def test_fast_dp_X4_wide(tmpdir):

  src = os.path.join(libtbx.env.under_build('xia2_regression'),
                     'test_data', 'X4_wide')
  dls = '/dls/science/groups/scisoft/DIALS/repositories/current/' + \
    'xia2_regression_data/test_data/X4_wide'
  if not os.path.exists(src):
    if not os.path.exists(dls):
      pytest.skip('Could not find test image file')
    src = dls

  image = os.path.join(src, 'X4_wide_M1S4_2_0001.cbf')

  bin = os.path.split(__file__)[0].replace('src', 'bin')
  fast_dp = os.path.join(bin, 'fast_dp')

  cmd = [ fast_dp, '-a', 'Ba', image ]
  with tmpdir.as_cwd():
    result = procrunner.run(cmd)

  assert result['stderr'] == '', 'fast_dp output to STDERR:'
  assert result['exitcode'] == 0, 'fast_dp non-zero exit code'
  for output in ['fast_dp.mtz', 'fast_dp.log']:
    assert tmpdir.join(output).check(), 'No output found'
