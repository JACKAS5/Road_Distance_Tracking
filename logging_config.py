import logging

class SuppressBrokenPipe(logging.Filter):
    def filter(self, record):
        return not ('Broken pipe' in record.getMessage())

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'suppress_broken_pipe': {
            '()': SuppressBrokenPipe,
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['suppress_broken_pipe'],
            'level': 'INFO',
        },
    },
    'loggers': {
        'uvicorn': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'uvicorn.error': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'uvicorn.access': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}