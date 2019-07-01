import logging
LOG_BASIC = 20
LOG_VERBOSE = 19
LOG_VDEBUG = 18
LOG_VVERBOSE = 17
LOG_VVDEBUG = 16
LOG_VVVERBOSE = 15
LOG_VPARAMS = 14
logging.addLevelName(LOG_VERBOSE, "verbose")
logging.addLevelName(LOG_VVERBOSE, "vverbose")
logging.addLevelName(LOG_VVVERBOSE, "vvverbose")
logging.addLevelName(LOG_VDEBUG, "vdebug")
logging.addLevelName(LOG_VVDEBUG, "vvdebug")
logging.addLevelName(LOG_VPARAMS, "vparams")


def basic(self, message, *args, **kws):
    if self.isEnabledFor(LOG_BASIC):
        # Yes, logger takes its '*args' as 'args'.
        self._log(LOG_BASIC, message, args, **kws)


def verbose(self, message, *args, **kws):
    if self.isEnabledFor(LOG_VERBOSE):
        # Yes, logger takes its '*args' as 'args'.
        self._log(LOG_VERBOSE, message, args, **kws)


def vverbose(self, message, *args, **kws):
    if self.isEnabledFor(LOG_VVVERBOSE):
        # Yes, logger takes its '*args' as 'args'.
        self._log(LOG_VVERBOSE, message, args, **kws)


def vvverbose(self, message, *args, **kws):
    if self.isEnabledFor(LOG_VVVERBOSE):
        # Yes, logger takes its '*args' as 'args'.
        self._log(LOG_VVVERBOSE, message, args, **kws)


def vdebug(self, message, *args, **kws):
    if self.isEnabledFor(LOG_VDEBUG):
        # Yes, logger takes its '*args' as 'args'.
        self._log(LOG_VDEBUG, message, args, **kws)


def vvdebug(self, message, *args, **kws):
    if self.isEnabledFor(LOG_VVDEBUG):
        # Yes, logger takes its '*args' as 'args'.
        self._log(LOG_VVDEBUG, message, args, **kws)


def vparams(self, message, *args, **kws):
    if self.isEnabledFor(LOG_VPARAMS):
        # Yes, logger takes its '*args' as 'args'.
        self._log(LOG_VPARAMS, message, args, **kws)


logging.Logger.basic = basic
logging.Logger.verbose = verbose
logging.Logger.vverbose = vverbose
logging.Logger.vvverbose = vvverbose
logging.Logger.vdebug = vdebug
logging.Logger.vvdebug = vvdebug
logging.Logger.vparams = vparams
