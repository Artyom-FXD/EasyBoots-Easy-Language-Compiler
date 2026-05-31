/**
 * file_native.c — Native C implementation for the File module.
 *
 * Extended file operations not provided by ely_runtime.c.
 * Dependencies: ely_runtime.h (for ely_file_open, ely_file_close, etc.)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <errno.h>

#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#else
#include <unistd.h>
#include <limits.h>
#endif

#include "../../runtime/ely_runtime.h"

/* ---------------- Extended Read / Write ---------------- */

char* ely_file_read_all_simple(const char* path) {
    return ely_file_read_all(path, NULL);
}

int ely_file_write_all_simple(const char* path, const char* data) {
    return ely_file_write_all(path, data, strlen(data));
}

/* ---------------- Metadata ---------------- */

long long ely_file_size(const char* path) {
    struct stat st;
    if (stat(path, &st) != 0) return -1;
    return (long long)st.st_size;
}

int ely_file_is_dir(const char* path) {
    struct stat st;
    if (stat(path, &st) != 0) return 0;
    return S_ISDIR(st.st_mode) ? 1 : 0;
}

int ely_file_is_file(const char* path) {
    struct stat st;
    if (stat(path, &st) != 0) return 0;
    return S_ISREG(st.st_mode) ? 1 : 0;
}

int ely_file_mkdir(const char* path) {
#ifdef _WIN32
    return _mkdir(path);
#else
    return mkdir(path, 0755);
#endif
}

int ely_file_rmdir(const char* path) {
#ifdef _WIN32
    return _rmdir(path);
#else
    return rmdir(path);
#endif
}