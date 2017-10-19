import subprocess


class SmartInfo(dict):

    @property
    def capacity_str(self):
        raw = self.get('user capacity')
        if raw:
            return raw.split('[')[-1].split(']')[0]

    @property
    def make_and_model(self):

        make = self.get('vendor')
        model = self.get('product')

        if not (make and model):
            model = self.get('device model')
            if model:
                try:
                    make, model = model.split(None, 1)
                except ValueError:
                    make = None

        return make, model


def parse_info(input_):
    data = SmartInfo()
    for line in input_.splitlines():
        parts = line.split(':', 1)
        if len(parts) == 2:
            data[parts[0].strip().lower()] = parts[1].strip()
    return data

def get_dev_info(dev):
    return parse_info(subprocess.check_output(['smartctl', '-i', dev]))
