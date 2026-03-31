#include "collections.h"
#include <stdlib.h>
#include <string.h>

// ------------------------ arr ------------------------
arr* arr_new(size_t elem_size) {
    arr* a = (arr*)malloc(sizeof(arr));
    if (!a) return NULL;
    a->data = NULL;
    a->size = 0;
    a->capacity = 0;
    a->elem_size = elem_size;
    return a;
}

void arr_free(arr* a) {
    if (a) {
        free(a->data);
        free(a);
    }
}

void arr_reserve(arr* a, size_t new_cap) {   // было static void arr_reserve
    if (new_cap <= a->capacity) return;
    void* new_data = realloc(a->data, new_cap * a->elem_size);
    if (!new_data) return;
    a->data = new_data;
    a->capacity = new_cap;
}

void arr_push(arr* a, void* elem) {
    if (!a) return;
    if (a->size >= a->capacity) {
        size_t new_cap = a->capacity == 0 ? 4 : a->capacity * 2;
        arr_reserve(a, new_cap);
    }
    memcpy((char*)a->data + a->size * a->elem_size, elem, a->elem_size);
    a->size++;
}

void* arr_pop_value(arr* a) {
    if (!a || a->size == 0) return NULL;
    a->size--;
    return (char*)a->data + a->size * a->elem_size;
}

void arr_pop(arr* a) {
    if (a && a->size > 0) a->size--;
}

void* arr_get(arr* a, size_t index) {
    if (!a || index >= a->size) return NULL;
    return (char*)a->data + index * a->elem_size;
}

void arr_set(arr* a, size_t index, void* elem) {
    if (!a || index >= a->size) return;
    memcpy((char*)a->data + index * a->elem_size, elem, a->elem_size);
}

size_t arr_len(arr* a) {
    return a ? a->size : 0;
}

int arr_remove_value(arr* a, void* value) {
    if (!a || a->size == 0) return -1;
    for (size_t i = 0; i < a->size; i++) {
        if (memcmp((char*)a->data + i * a->elem_size, value, a->elem_size) == 0) {
            size_t bytes = (a->size - i - 1) * a->elem_size;
            memmove((char*)a->data + i * a->elem_size,
                    (char*)a->data + (i + 1) * a->elem_size, bytes);
            a->size--;
            return 0;
        }
    }
    return -1;
}

int arr_remove_index(arr* a, size_t index) {
    if (!a || index >= a->size) return -1;
    size_t bytes = (a->size - index - 1) * a->elem_size;
    memmove((char*)a->data + index * a->elem_size,
            (char*)a->data + (index + 1) * a->elem_size, bytes);
    a->size--;
    return 0;
}

int arr_insert(arr* a, size_t index, void* elem) {
    if (!a || index > a->size) return -1;
    if (a->size >= a->capacity) {
        size_t new_cap = a->capacity == 0 ? 4 : a->capacity * 2;
        arr_reserve(a, new_cap);
    }
    size_t bytes = (a->size - index) * a->elem_size;
    memmove((char*)a->data + (index + 1) * a->elem_size,
            (char*)a->data + index * a->elem_size, bytes);
    memcpy((char*)a->data + index * a->elem_size, elem, a->elem_size);
    a->size++;
    return 0;
}

int arr_index(arr* a, void* value) {
    if (!a) return -1;
    for (size_t i = 0; i < a->size; i++) {
        if (memcmp((char*)a->data + i * a->elem_size, value, a->elem_size) == 0)
            return (int)i;
    }
    return -1;
}

arr* arr_copy(arr* a) {
    if (!a) return NULL;
    arr* copy = arr_new(a->elem_size);
    if (!copy) return NULL;
    arr_reserve(copy, a->capacity);
    memcpy(copy->data, a->data, a->size * a->elem_size);
    copy->size = a->size;
    return copy;
}

arr* arr_make(size_t count, size_t elem_size, ...) {
    arr* a = arr_new(elem_size);
    if (!a) return NULL;
    va_list args;
    va_start(args, elem_size);
    for (size_t i = 0; i < count; i++) {
        void* elem = va_arg(args, void*);
        arr_push(a, elem);
    }
    va_end(args);
    return a;
}

// ------------------------ dict ------------------------
static unsigned int default_hash(void* key) {
    unsigned int h = 0;
    unsigned char* p = (unsigned char*)key;
    for (size_t i = 0; i < sizeof(unsigned int); i++)
        h = (h << 5) + p[i];
    return h;
}

static int default_cmp(void* a, void* b) {
    return memcmp(a, b, sizeof(unsigned int));
}

dict* dict_new(size_t key_size, size_t value_size,
               unsigned int (*hash)(void*),
               int (*key_cmp)(void*, void*)) {
    dict* d = (dict*)malloc(sizeof(dict));
    if (!d) return NULL;
    d->capacity = 16;
    d->buckets = (dict_entry**)calloc(d->capacity, sizeof(dict_entry*));
    if (!d->buckets) { free(d); return NULL; }
    d->size = 0;
    d->key_size = key_size;
    d->value_size = value_size;
    d->hash = hash ? hash : default_hash;
    d->key_cmp = key_cmp ? key_cmp : default_cmp;
    return d;
}

void dict_free(dict* d) {
    if (!d) return;
    for (size_t i = 0; i < d->capacity; i++) {
        dict_entry* e = d->buckets[i];
        while (e) {
            dict_entry* next = e->next;
            free(e->key);
            free(e->value);
            free(e);
            e = next;
        }
    }
    free(d->buckets);
    free(d);
}

static void dict_resize(dict* d, size_t new_cap) {
    if (new_cap < d->size) return;
    dict_entry** new_buckets = (dict_entry**)calloc(new_cap, sizeof(dict_entry*));
    if (!new_buckets) return;
    for (size_t i = 0; i < d->capacity; i++) {
        dict_entry* e = d->buckets[i];
        while (e) {
            dict_entry* next = e->next;
            size_t idx = d->hash(e->key) % new_cap;
            e->next = new_buckets[idx];
            new_buckets[idx] = e;
            e = next;
        }
    }
    free(d->buckets);
    d->buckets = new_buckets;
    d->capacity = new_cap;
}

void dict_set(dict* d, void* key, void* value) {
    if (!d) return;
    if (d->size >= d->capacity * 0.75) {
        dict_resize(d, d->capacity * 2);
    }
    unsigned int h = d->hash(key);
    size_t idx = h % d->capacity;
    dict_entry* e = d->buckets[idx];
    while (e) {
        if (d->key_cmp(e->key, key) == 0) {
            memcpy(e->value, value, d->value_size);
            return;
        }
        e = e->next;
    }
    e = (dict_entry*)malloc(sizeof(dict_entry));
    if (!e) return;
    e->key = malloc(d->key_size);
    e->value = malloc(d->value_size);
    if (!e->key || !e->value) { free(e->key); free(e->value); free(e); return; }
    memcpy(e->key, key, d->key_size);
    memcpy(e->value, value, d->value_size);
    e->next = d->buckets[idx];
    d->buckets[idx] = e;
    d->size++;
}

void* dict_get(dict* d, void* key) {
    if (!d) return NULL;
    unsigned int h = d->hash(key);
    size_t idx = h % d->capacity;
    dict_entry* e = d->buckets[idx];
    while (e) {
        if (d->key_cmp(e->key, key) == 0)
            return e->value;
        e = e->next;
    }
    return NULL;
}

int dict_has(dict* d, void* key) {
    if (!d) return 0;
    unsigned int h = d->hash(key);
    size_t idx = h % d->capacity;
    dict_entry* e = d->buckets[idx];
    while (e) {
        if (d->key_cmp(e->key, key) == 0)
            return 1;
        e = e->next;
    }
    return 0;
}

int dict_delete(dict* d, void* key) {
    if (!d) return -1;
    unsigned int h = d->hash(key);
    size_t idx = h % d->capacity;
    dict_entry* e = d->buckets[idx];
    dict_entry* prev = NULL;
    while (e) {
        if (d->key_cmp(e->key, key) == 0) {
            if (prev) prev->next = e->next;
            else d->buckets[idx] = e->next;
            free(e->key);
            free(e->value);
            free(e);
            d->size--;
            return 0;
        }
        prev = e;
        e = e->next;
    }
    return -1;
}

size_t dict_size(dict* d) {
    return d ? d->size : 0;
}

arr* dict_keys(dict* d) {
    if (!d) return NULL;
    arr* keys = arr_new(d->key_size);
    if (!keys) return NULL;
    for (size_t i = 0; i < d->capacity; i++) {
        dict_entry* e = d->buckets[i];
        while (e) {
            arr_push(keys, e->key);
            e = e->next;
        }
    }
    return keys;
}

arr* dict_values(dict* d) {
    if (!d) return NULL;
    arr* values = arr_new(d->value_size);
    if (!values) return NULL;
    for (size_t i = 0; i < d->capacity; i++) {
        dict_entry* e = d->buckets[i];
        while (e) {
            arr_push(values, e->value);
            e = e->next;
        }
    }
    return values;
}

dict* dict_make(size_t count, size_t key_size, size_t value_size,
                unsigned int (*hash)(void*),
                int (*key_cmp)(void*, void*), ...) {
    dict* d = dict_new(key_size, value_size, hash, key_cmp);
    if (!d) return NULL;
    va_list args;
    va_start(args, key_cmp);
    for (size_t i = 0; i < count; i++) {
        void* key = va_arg(args, void*);
        void* value = va_arg(args, void*);
        dict_set(d, key, value);
    }
    va_end(args);
    return d;
}

// Обёртки для строковых ключей
unsigned int dict_hash_str(void* key) {
    unsigned int hash = 5381;
    char* str = (char*)key;
    int c;
    while ((c = *str++))
        hash = ((hash << 5) + hash) + c;
    return hash;
}

int dict_cmp_str(void* a, void* b) {
    return strcmp((char*)a, (char*)b);
}

dict* dict_new_str(size_t value_size) {
    return dict_new(sizeof(char*), value_size, dict_hash_str, dict_cmp_str);
}

void dict_set_str(dict* d, char* key, void* value) {
    dict_set(d, &key, value);
}

void* dict_get_str(dict* d, char* key) {
    return dict_get(d, &key);
}

int dict_has_str(dict* d, char* key) {
    return dict_has(d, &key);
}

int dict_delete_str(dict* d, char* key) {
    return dict_delete(d, &key);
}

arr* dict_keys_str(dict* d) {
    return dict_keys(d);  // ключи уже char*
}