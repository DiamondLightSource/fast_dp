from __future__ import absolute_import, division, print_function


def XDS_INP_to_dict(inp_text):
    result = {}
    for record in inp_text.split("\n"):
        useful = record.split("!")[0].strip()
        if not useful:
            continue
        if useful.count("=") > 1:
            # assume tokens of form key=value key=value
            tokens = useful.replace("=", " ").split()
            for j in range(useful.count("=")):
                key = tokens[2 * j].strip()
                value = tokens[2 * j + 1].strip()
                # handle multiples gracelessly
                if key in result:
                    if not isinstance(result[key], list):
                        result[key] = [result[key]]
                        result[key].append(value)
                    else:
                        result[key].append(value)
                else:
                    result[key] = value
        else:
            tokens = useful.split("=")
            key = tokens[0].strip()
            value = tokens[1].strip()
            # handle multiples gracelessly
            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                    result[key].append(value)
                else:
                    result[key].append(value)
            else:
                result[key] = value

    return result


def diff(xds_inp_a, xds_inp_b):
    """Compare the parameters in a, b; write out the differences"""

    all_keys = list(sorted(set(xds_inp_a).union(xds_inp_b)))

    for key in all_keys:
        a = xds_inp_a.get(key, "")
        b = xds_inp_b.get(key, "")
        if a == b:
            continue
        print("%s:\n\t%s\n\t%s" % (key, a, b))


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        raise RuntimeError("%s XDS.INP ../other/XDS.INP" % sys.argv[1])

    a = XDS_INP_to_dict(open(sys.argv[1]).read())
    b = XDS_INP_to_dict(open(sys.argv[2]).read())
    diff(a, b)
