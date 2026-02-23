import functools
import logging
import time


def logging_info_generator(info: str, total_length: int = 100, fill: str = "█", style: str = "MID") -> str:
    """
    Add padding to the info, so the total length = 100
    :param info: logging info
    :param total_length: total length of the info
    :param fill: padding character
    :param style:
        mid-padding     -> put info in the middle ████████ info ████████
        right-padding   -> put info to the left   info██████████████████
        left-padding    -> put info to the right  ██████████████████info
    :return:
    """
    if style == "MID":
        fill_length = int((total_length - len(info)) // 2)
        info = fill * fill_length + info + fill * fill_length
    else:
        fill_length = int((total_length - len(info)))
        info = fill * fill_length + info if style == "RIGHT" else info + fill * fill_length

    # 2 may cause 1 space difference, so fill empty
    info += fill * (total_length - len(info))
    return info


def log(log_info: str, log_level: str = "PROCESS", fill: str = "█"):
    """
    define decorator for logging
    :param log_info: logging info
    :param log_level: log level, can be process or step
    :param fill: fill the
    :return:
    """
    def process_log_decorator(func):
        """
        process logging
        :param func: function to wrap
        :return:
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # ################### BEFORE RUNNING FUNCTION ####################
                start_info = log_info
                start_info = logging_info_generator(start_info, fill=fill)

                logging.info('\n')
                logging.info(start_info)
                start = time.time()
                # ################### BEFORE RUNNING FUNCTION ####################

                # ################### RUNNING FUNCTION ####################
                result = func(*args, **kwargs)
                # ################### RUNNING FUNCTION ####################

                # ################### AFTER RUNNING FUNCTION ####################
                end = time.time()
                end_info = "{}".format(log_info)
                end_info = logging_info_generator(end_info, fill=fill)
                logging.info('Process done, executing time {} secs'.format(end - start))
                logging.info(end_info)
                # ################### AFTER RUNNING FUNCTION ####################

                return result
            except Exception as e:
                logging.exception(f"Exception raised in {func.__name__}. exception: {str(e)}")
                raise e

        return wrapper

    def step_log_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # ################### BEFORE RUNNING FUNCTION ####################
                logging.info("{}".format(log_info))
                start = time.time()
                # ################### BEFORE RUNNING FUNCTION ####################

                # ################### RUNNING FUNCTION ####################
                result = func(*args, **kwargs)
                # ################### RUNNING FUNCTION ####################

                # ################### AFTER RUNNING FUNCTION ####################
                end = time.time()
                logging.info("---------> Step done, executing time {} secs".format(end - start))
                # ################### AFTER RUNNING FUNCTION ####################

                return result
            except Exception as e:
                logging.exception(f"Exception raised in {func.__name__}. exception: {str(e)}")
                raise e

        return wrapper

    if log_level == 'PROCESS':
        return process_log_decorator
    else:
        return step_log_decorator