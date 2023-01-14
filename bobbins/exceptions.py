class BaseBobbinsException(Exception):
    ...


class ProvidedConfigDoesNotExist(BaseBobbinsException):
    ...


class ProvidedConfigIsInvalid(BaseBobbinsException):
    ...


class ProvidedForumChannelIDIsInvalid(BaseBobbinsException):
    ...


class RequiredEnvironmentVariableIsNotSet(BaseBobbinsException):
    ...
