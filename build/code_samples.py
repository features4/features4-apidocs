import os
from pathlib import Path
import json

from jinja2 import Environment, FileSystemLoader


def single_quotes(d):
    return d.replace('"', "'")


def to_nice_json(d):
    return json.dumps(d, indent=2)


def is_flat(d):
    for val in d.values():
        if isinstance(val, (dict, list)):
            return False
    return True


dirname = os.path.dirname(__file__)
env = Environment(
    loader=FileSystemLoader(os.path.join(dirname, "code_templates")),
    trim_blocks=True,
)
env.policies["json.dumps_kwargs"] = {"sort_keys": False}

env.filters["to_nice_json"] = to_nice_json
env.filters["single_quotes"] = single_quotes
env.filters["is_flat"] = is_flat

samples = {}

lat = 48.137
lng = 11.576

base_url = "https://api.features4.com/v1"
api_key = "API_TEST_KEY"

base_params = {"base_url": base_url, "api_key": api_key}

features_params = {
    "features": [
        {
            "endpoint": "/number",
            "params": {"lat": lat, "lng": lng, "element": "bar", "radius": 500},
        },
        {
            "endpoint": "/distance",
            "params": {"lat": lat, "lng": lng, "element": "atm"},
        },
    ]
}

analysis = {
    "number": {
        "method": "post",
        "params": {"lat": lat, "lng": lng, "element": "bar", "radius": 500},
    },
    "distance": {
        "method": "post",
        "params": {"lat": lat, "lng": lng, "element": "bar"},
    },
    "elements": {"method": "post", "params": {"lat": lat, "lng": lng}},
    "features": {"method": "post", "params": features_params},
}

languages = ["Python", "R", "Shell"]


class CodeSampleTemplate:
    extensions = {"Python": "py", "R": "R", "Shell": "sh"}

    def __init__(self, env, language, method, endpoint, params, **kwargs):
        self.env = env
        self.language = language
        self.method = method
        self.extension = self.extensions[self.language]
        self.endpoint = endpoint
        self.params = params
        for arg_name, arg_val in kwargs.items():
            setattr(self, arg_name, arg_val)

    def render(self, *args, **kwargs):
        template = env.get_template(self.template_path)
        rendered = template.render(
            params=self.params, endpoint=self.endpoint, *args, **kwargs
        )
        return rendered

    @property
    def template_path(self):
        return self.language + "/" + self.method


templates = []
for lang in languages:
    for endpoint, settings in analysis.items():
        templates.append(
            CodeSampleTemplate(
                env=env,
                language=lang,
                method=settings["method"],
                endpoint=endpoint,
                params=settings["params"],
            )
        )


def main():
    templates_json = {"samples": {}}
    for template in templates:
        rendered = template.render(**base_params)

        p = Path(dirname).parent
        fname = (
            p
            / "openapi/code_samples"
            / template.language
            / template.endpoint
            / (template.method + "." + template.extension)
        )
        fname.write_text(rendered)

        if template.endpoint not in templates_json["samples"]:
            templates_json["samples"][template.endpoint] = {}
        templates_json["samples"][template.endpoint].update(
            {template.language.lower(): rendered}
        )

    fname = "/home/philipp/Documents/geo/geofeatures/docs/src/json/code_samples.json"
    with open(fname, "w") as f:
        json.dump(templates_json, f)


if __name__ == "__main__":
    main()
