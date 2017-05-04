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

import pytest

def test_fast_dp_X4_wide():
  import os
  import libtbx.load_env
  from dials.util.procrunner import run_process
  import tempfile

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
  
  cmd = '%s -a Ba %s' % (fast_dp, image)

  run = tempfile.mkdtemp()

  os.chdir(run)
  result = run_process(cmd.split())

  assert result['stderr'] == '', 'fast_dp output to STDERR:' + result['stderr']
  assert result['exitcode'] == 0, 'fast_dp exit code != 0: %d' % \
    result['exitcode']
  for output in ['fast_dp.mtz', 'fast_dp.log']:
    assert os.path.exists(os.path.join(run, output)), 'No output found'

def test_are_there_any_real_tests():
  assert True, "So test! Much happy!"
