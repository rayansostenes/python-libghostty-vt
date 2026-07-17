/*
 * Empty stub replacing the real <stdbool.h> during cdef generation.
 *
 * The real header defines `bool` as a macro for `_Bool`. cffi's cdef parser
 * accepts `bool` directly, so the token is left untouched here rather than
 * expanded, keeping the generated cdef readable. See stddef.h for the rationale.
 */
