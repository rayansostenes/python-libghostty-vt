/*
 * Stub replacing the real <limits.h> during cdef generation.
 *
 * Upstream sizes its C enums to `int` on pre-C23 compilers by appending an
 * `INT_MAX` sentinel member (see GHOSTTY_ENUM_MAX_VALUE in types.h). cffi's cdef
 * parser cannot resolve the identifier `INT_MAX`, so this stub expands it to the
 * literal value every supported platform uses for a 32-bit int. In cffi API
 * mode the value is cross-checked against the real headers at compile time.
 */
#define INT_MAX 2147483647
