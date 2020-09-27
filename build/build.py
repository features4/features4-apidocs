#!/usr/bin/env python3
import sys
import yaml
import subprocess

def yaml_to_cli(d):
    res = []

    def dict_to_string(item, string):
        if not isinstance(item, dict):
            res.append(string)
            res.append(str(item))
        else:
            for k, v in item.items():
                dict_to_string(v, string + '.' + k)

    dict_to_string(d, '--options')
    return res


def main(schema_fname='schema/schema.yaml'):
    redoc_yaml_file = '.redocly.yaml'
    redoc_args = ['npx', 'redoc-cli', 'bundle', '-t', 'html/index.html', '-o', 'index.html']
    with open(redoc_yaml_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        options_args = yaml_to_cli(config['referenceDocs'])
    args = redoc_args + options_args + [schema_fname]
    subprocess.call(args)


if __name__ == '__main__': 
    if len(sys.argv) > 1:
        main(schema_fname=sys.argv[1])
    else:
        main()
