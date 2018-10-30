## Minimal intro "How to make a test":

1. Files matching pattern test_*.py contain tests.
2. Functions matching pattern test_* are tests.

3. To run the tests in a dials distribution, install dlstbx and run

       py.test

## Advanced stuff

4. To automatically run tests on file changes, run

       ptw     # ("py.test watch")

5. Use asserts, generally no need to create or import other
   assert implementations.
   eg.

   ```python
   def test_assert():
     assert [1,2,3] == [1,2,4]
   ```

   will give you the following output:

   ```python
      def test_assert():
   >    assert [1,2,3] == [1,2,4]
   E    assert [1, 2, 3] == [1, 2, 4]
   E      At index 2 diff: 3 != 4
   E      Use -v to get the full diff
   ```

6. more advanced stuff at https://docs.pytest.org/en/latest/
