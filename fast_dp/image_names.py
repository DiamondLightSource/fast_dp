from __future__ import absolute_import, division, print_function

import math
import os
import re
import string

def image2template(filename):
    '''Return a template to match this filename.'''

    # check that the file name doesn't contain anything mysterious
    if filename.count('#'):
        raise RuntimeError('# characters in filename')

    # the patterns in the order I want to test them

    pattern_keys = [r'([^\.]*)\.([0-9]+)\Z',
                    r'(.*)_([0-9]*)\.(.*)',
                    r'(.*?)([0-9]*)\.(.*)']

    # patterns is a dictionary of possible regular expressions with
    # the format strings to put the file name back together

    patterns = {r'([^\.]*)\.([0-9]+)\Z':'%s.%s%s',
                r'(.*)_([0-9]*)\.(.*)':'%s_%s.%s',
                r'(.*?)([0-9]*)\.(.*)':'%s%s.%s'}

    for pattern in pattern_keys:
        match = re.compile(pattern).match(filename)

        if match:
            prefix = match.group(1)
            number = match.group(2)
            try:
                exten = match.group(3)
            except:
                exten = ''

            for digit in string.digits:
                number = number.replace(digit, '#')

            return patterns[pattern] % (prefix, number, exten)

    raise RuntimeError('filename %s not understood as a template' % \
          filename)

def image2image(filename):
    '''Return an integer for the template to match this filename.'''

    # check that the file name doesn't contain anything mysterious
    if filename.count('#'):
        raise RuntimeError('# characters in filename')

    # the patterns in the order I want to test them

    pattern_keys = [r'([^\.]*)\.([0-9]+)\Z',
                    r'(.*)_([0-9]*)\.(.*)',
                    r'(.*?)([0-9]*)\.(.*)']

    for pattern in pattern_keys:
        match = re.compile(pattern).match(filename)

        if match:
            prefix = match.group(1)
            number = match.group(2)
            try:
                exten = match.group(3)
            except:
                exten = ''

            return int(number)

    raise RuntimeError('filename %s not understood as a template' % \
          filename)

def image2template_directory(filename):
    '''Separate out the template and directory from an image name.'''

    directory = os.path.dirname(filename)

    if not directory:

        # then it should be the current working directory
        directory = os.getcwd()

    image = os.path.split(filename)[-1]
    template = image2template(image)

    return template, directory

def find_matching_images(template, directory):
    '''Find images which match the input template in the directory
    provided.'''

    files = os.listdir(directory)

    # to turn the template to a regular expression want to replace
    # however many #'s with EXACTLY the same number of [0-9] tokens,
    # e.g. ### -> ([0-9]{3})

    # change 30/may/2008 - now escape the template in this search to cope with
    # file templates with special characters in them, such as "+" -
    # fix to a problem reported by Joel B.

    length = template.count('#')
    regexp_text = re.escape(template).replace('\\#' * length,
                                              '([0-9]{%d})' % length)
    regexp = re.compile(regexp_text)

    images = []

    for f in files:
        match = regexp.match(f)

        if match:
            images.append(int(match.group(1)))

    images.sort()

    return images

def template_directory_number2image(template, directory, number):
    '''Construct the full path to an image from the template, directory
    and image number.'''

    length = template.count('#')

    # check that the number will fit in the template

    if (math.pow(10, length) - 1) < number:
        raise RuntimeError('number too big for template')

    # construct a format statement to give the number part of the
    # template
    format = '%%0%dd' % length

    # construct the full image name
    image = os.path.join(directory,
                         template.replace('#' * length,
                                          format % number))

    return image
