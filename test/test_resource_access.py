import fast_dp.output

def test_ispyb_xml_template_is_accessible():
  xml = fast_dp.output.get_ispyb_template()
  assert '<AutoProcContainer>' in xml
