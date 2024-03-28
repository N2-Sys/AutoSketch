#ifndef __AS_UTIL_H__
#define __AS_UTIL_H__

#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sched.h>
#include <assert.h>
#include "tuple.h"

#define MB (1024*1024)
#define GB (1024*1024*1024)

#define as_likely(x) __builtin_expect ((x), 1)
#define as_unlikely(x) __builtin_expect ((x), 0)

#define afs_assert(x, ...) \
    do {\
        if (afs_unlikely(!(x))) {\
            fprintf (stderr, "Assertion failed at %s (%s:%d): ", #x, \
                __FILE__, __LINE__);\
            fprintf (stderr, "" __VA_ARGS__);\
            fflush(stderr);\
            exit(EXIT_FAILURE);\
        }\
    } while (0) 

#define LOG_MSG(...) \
    do { \
        fprintf(stderr, __VA_ARGS__); \
        fflush(stderr);\
    } while (0)
#define LOG_WARN(...) \
    do { \
        fprintf(stderr, "[WARN] " __VA_ARGS__); \
        fflush(stderr);\
    } while(0)
#define LOG_ERR(...) \
    do { \
        fprintf(stderr, "[ERROR] "  __VA_ARGS__); \
        exit(EXIT_FAILURE); \
    } while (0)

#ifdef DEBUG
#define LOG_DEBUG(...) \
    do { \
        fprintf(stderr, "[DEBUG]" __VA_ARGS__); \
        fflush(stderr); \
    } while (0)
#else
#define LOG_DEBUG(...)
#endif

static inline uint64_t now_us ()
{
    //  Use POSIX gettimeofday function to get precise time.
    struct timeval tv;
    gettimeofday (&tv, NULL);
    return (tv.tv_sec * (uint64_t) 1000000 + tv.tv_usec);
}

static inline int cmp_lf (const void * a, const void * b) {
    return (*(double*)a) < (*(double*)b);
}

static inline int cmp_ll (const void * a, const void * b) {
    return (*(long long*)a) < (*(long long*)b);
}

static inline int cmp (const void * a, const void * b) {
    tuple_t* t1 = (tuple_t*)a;
    tuple_t* t2 = (tuple_t*)b;
    
    if (t1->size != t2->size) {
        return t1->size < t2->size;
    }
    
    if (t1->key.src_ip != t2->key.src_ip) {
        return t1->key.src_ip < t2->key.src_ip;
    }
    
    if (t1->key.dst_ip != t2->key.dst_ip) {
        return t1->key.dst_ip < t2->key.dst_ip;
    }
    
    if (t1->key.src_port != t2->key.src_port) {
        return t1->key.src_port < t2->key.src_port;
    }
    
    if (t1->key.dst_port != t2->key.dst_port) {
        return t1->key.dst_port < t2->key.dst_port;
    }
    
    return t1->key.proto < t2->key.proto;
}

#endif // AFS_UTIL_HPP_
