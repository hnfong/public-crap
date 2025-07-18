#!/usr/bin/env python3

import os
import sys
import re

"""
Mostly generated by Deepseek-R1-0528, with minor manual edits
Prompt:

I have a markdown file that looks like this (of course this is only a skeleton
and it will be expanded later). I want to add links to markdown scripts. For
example, I may have a software/neovim.md file which should be linked here as
[neovim](software/neovim.md) under the software category. Write a python script
to autogenerate the markdown output by editing the existing file. (Do not use a
template in the python script, just edit the existing file by cleverly
replacing and updating the sections under the headings (with two #)

```
# Reviews

I realized I need to write reviews of things I've used as a record, not
necessarily to share the information with others, but to serve as a record and
a reminder to my future self.

This is especially true for things that I have incidentally discovered, and
then due to my forgetfulness, gets thrown out of my conscious mind a short
while later.

That said, I'll also put reviews here for things that I've used for a lifetime.

## Software

## Food ingredients

## Books
```

Write the program. No need to explain.

"""
def update_markdown_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # Split content into lines and identify section boundaries
    lines = content.splitlines()
    sections = []
    current_heading = None
    start_index = 0

    for i, line in enumerate(lines):
        if re.match(r'^##\s+', line):
            if current_heading is not None:
                sections.append((current_heading, start_index, i))
            current_heading = line.strip()[3:].strip()
            start_index = i

    if current_heading is not None:
        sections.append((current_heading, start_index, len(lines)))

    # Rebuild content with updated sections
    new_content = []
    last_end = 0

    for heading, start, end in sections:
        # Preserve content before this section
        new_content.extend(lines[last_end:start])
        last_end = end

        # Add the section heading
        new_content.append(f'## {heading}')

        # Generate links for this section
        dir_name = heading.lower().replace(' ', '-')
        if os.path.isdir(dir_name):
            md_files = sorted(
                [f for f in os.listdir(dir_name) if f.endswith('.md')],
                key=lambda x: x.lower()
            )
            links = [
                f"- [{os.path.splitext(f)[0]}]({dir_name}/{f})"
                for f in md_files
            ]
            new_content.append('')  # Maintain empty section if no files
            if links:
                new_content.extend(links)
            new_content.append('')  # Maintain empty section if no files
        else:
            new_content.extend(lines[start+1:end])  # Keep original content

    # Add remaining content after last section
    new_content.extend(lines[last_end:])

    # Write updated content back to file
    with open(filename, 'w') as f:
        f.write('\n'.join(new_content))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        # print(f"Usage: {sys.argv[0]} <markdown_file>")
        # sys.exit(1)
        update_markdown_file("README.md")
    else:

        update_markdown_file(sys.argv[1])
