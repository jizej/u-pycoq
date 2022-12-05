"""
TODO


--
    pycoq_logfile_name: Path = Path(pycoq.config.DEFAULT_CONFIG['log_filename']).expanduser()
    clear_file_contents(pycoq_logfile_name)

"""
import time


def mine_data():
    pass

if __name__ == '__main__':
    start_time = time.time()
    mine_data()
    duration = time.time() - start_time
    print(f"{duration=}\n\a")

    print('---- done!\a\n')