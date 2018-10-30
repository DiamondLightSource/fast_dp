from __future__ import absolute_import, division, print_function

import mock
import os
import pytest
import sys

def test_fast_dp_X4_wide(capsys, tmpdir):
  X4_wide = '/dls/science/groups/scisoft/DIALS/regression_data/X4_wide'
  if not os.path.exists(X4_wide):
    pytest.skip('Could not find test image file')

  image = os.path.join(X4_wide, 'X4_wide_M1S4_2_0001.cbf')

  cmd = [ 'fast_dp', '-a', 'Ba', image ]
  with tmpdir.as_cwd():
    with mock.patch.object(sys, 'argv', cmd):
      import fast_dp.fast_dp
      fast_dp.fast_dp.main()

  captured = capsys.readouterr()
  assert captured.err == '', 'fast_dp output to STDERR:'
  for output in ['fast_dp.mtz', 'fast_dp.log']:
    assert tmpdir.join(output).check(), 'No output found'
