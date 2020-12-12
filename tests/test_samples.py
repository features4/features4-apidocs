import pdb
import re
import pytest
import subprocess
import logging
import shutil
import yaml
import tempfile
import os

from copy import deepcopy
from pathlib import Path

log = logging.getLogger(__name__)

class CodeSample:
    def __init__(self, endpoint, method, lang, source):
        self.endpoint = endpoint
        self.method = method
        self.lang = lang
        self.source = source
    
def get_code_samples(schema_path):
    """Extract code samples from schema and group by language and method"""
    with open(schema_path, 'r') as f:
        schema = yaml.safe_load(f)
    samples = []
    for path, method_description in schema["paths"].items():
        for method, description in method_description.items():
            print(description)
            for example in description.get("x-code-samples", []):
                lang = example["lang"]
                source = example["source"]
                sample = CodeSample(endpoint=path, method=method, lang=lang, source=source)
                samples.append(sample)
    print(samples)
    return samples


    

class SampleHandler:
    status_code_msg = None
    subprocess_args = None

    def __init__(self, sample, environment='production'):
        self.sample = deepcopy(sample)
        self.environment = environment

    def change_api_key(self):
        self.sample.source = self.sample.source.replace('API_TEST_KEY', os.environ["API_TEST_KEY"])

    def change_base_url(self, url='http://localhost:8000/v1'):
        self.sample.source = self.sample.source.replace(base_url, url)

    def add_status_code_message(self):
        self.sample.source = self.sample.source + self.status_code_msg

    def run(self):
        if self.environment == 'development':
            self.change_base_url()
        self.change_api_key()
        self.add_status_code_message()
        result = self.run_subprocess()
        return result

    def run_subprocess(self):
        handle, path = tempfile.mkstemp(suffix=self.extension)
        with open(path, 'w') as f:
            f.write(self.sample.source)
        args = self.subprocess_args + [path]
        result = None
        try: 
            result = subprocess.run(args, capture_output=True, text=True, check=False)
        except:
            pass
        finally:
            os.remove(path)
        return result


class RHandler(SampleHandler):
    status_code_msg = '\nwrite(r$status_code, stderr())'
    subprocess_args = ['Rscript']
    extension = ".R"

class PythonHandler(SampleHandler):
    status_code_msg = '\nimport sys;sys.stderr.write(str(r.status_code))'
    subprocess_args = ['python']
    extension = ".py"

class ShellHandler(SampleHandler):
    status_code_msg = ' -s -o /dev/null -w "%{http_code}\\n" 1>&2'
    subprocess_args = ['/bin/sh']
    extension = ".sh"



def get_language_handler(lang):
    lang = lang.lower()
    if lang == 'python':
        return PythonHandler
    elif lang == 'r':
        return RHandler
    elif lang == 'shell':
        return ShellHandler
    else:
        raise Exception(f"No handler found for lang {lang}")

path = Path('./schema/schema.yaml')
samples = get_code_samples(schema_path=path)

base_url = 'https://api.features4.com/v1'

@pytest.mark.parametrize('environment', ['production', 'development'])
@pytest.mark.parametrize('sample', samples)
def test_code_sample(sample, environment):
    handler = get_language_handler(sample.lang)
    h = handler(sample=sample, environment=environment)
    s = h.run()
    assert s.stderr.strip() == '200'


if __name__ == '__main__':
    environments = ["production", "development"]
    for environment in environments:
        for sample in samples:
            print(environment, sample.endpoint, sample.lang)
            test_code_sample(sample, environment)
