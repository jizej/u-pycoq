"""
TODO


--
    pycoq_logfile_name: Path = Path(pycoq.config.DEFAULT_CONFIG['log_filename']).expanduser()
    clear_file_contents(pycoq_logfile_name)

"""
import time

from pycoq.config import clear_pycoq_logging_file


def mine_data():
    pass


if __name__ == '__main__':
    clear_pycoq_logging_file()
    start_time = time.time()
    mine_data()
    duration = time.time() - start_time
    print(f"{duration=}\n\a")

    print('---- done!\a\n')
