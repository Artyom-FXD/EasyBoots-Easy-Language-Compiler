#include "dictserver.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

struct DictServer {
    char* path;           // путь к файлу (для сохранения)
    easy_dict* root;      // корневой объект
};

// Вспомогательные функции для разбора пути
static char* next_segment(char* path, char** next) {
    char* dot = strchr(path, '.');
    if (dot) {
        size_t len = dot - path;
        char* seg = easy_alloc(len + 1);
        memcpy(seg, path, len);
        seg[len] = '\0';
        *next = dot + 1;
        return seg;
    } else {
        char* seg = easy_str_dup(path);
        *next = NULL;
        return seg;
    }
}

// Получение узла по пути (создание, если create=1)
static void* get_node(DictServer* ds, char* path, int create, int* is_array) {
    if (!path || !*path) return ds->root;
    char* cur = path;
    void* current = ds->root;
    void* parent = NULL;
    char* last_seg = NULL;
    int last_is_array = 0;

    while (cur) {
        char* seg = next_segment(cur, &cur);
        // Если сегмент – число, то работаем с массивом
        int index = -1;
        char* endptr;
        long idx = strtol(seg, &endptr, 10);
        if (*endptr == '\0') {
            index = (int)idx;
            // текущий узел должен быть массивом
            if (!current) {
                if (!create) { easy_free(seg); return NULL; }
                // создать массив
                current = easy_array_new(0, sizeof(void*));
                if (parent) {
                    if (last_is_array) {
                        // parent – массив, last_seg – индекс
                        easy_array_set(parent, (size_t)index, &current);
                    } else {
                        // parent – словарь, last_seg – ключ
                        easy_dict_set(parent, last_seg, &current);
                    }
                } else {
                    ds->root = current;
                }
            }
            if (!current) { easy_free(seg); return NULL; }
            // Проверим, что current – массив
            // В нашей реализации мы не храним тип явно, поэтому будем предполагать, что если узел – easy_array*, то это массив.
            // Для простоты будем проверять, что это указатель на easy_array, но это ненадёжно. Лучше хранить тип.
            // Пока сделаем предположение.
            if (cur == NULL) {
                // последний сегмент – индекс, возвращаем элемент массива
                if (is_array) *is_array = 1;
                void* elem = easy_array_get(current, (size_t)index);
                if (elem) return *(void**)elem;
                if (create) {
                    void* new_elem = NULL;
                    easy_array_set(current, (size_t)index, &new_elem);
                    return &new_elem;
                }
                return NULL;
            } else {
                // переходим в элемент массива
                void* elem_ptr = easy_array_get(current, (size_t)index);
                if (!elem_ptr && create) {
                    void* new_elem = NULL;
                    easy_array_set(current, (size_t)index, &new_elem);
                    elem_ptr = &new_elem;
                }
                parent = current;
                last_seg = seg;
                last_is_array = 1;
                current = elem_ptr ? *(void**)elem_ptr : NULL;
                continue;
            }
        } else {
            // работаем со словарём
            if (!current) {
                if (!create) { easy_free(seg); return NULL; }
                // создать словарь
                current = easy_dict_new(8, sizeof(void*));
                if (parent) {
                    if (last_is_array) {
                        easy_array_set(parent, (size_t)index, &current);
                    } else {
                        easy_dict_set(parent, last_seg, &current);
                    }
                } else {
                    ds->root = current;
                }
            }
            if (!current) { easy_free(seg); return NULL; }
            if (cur == NULL) {
                // последний сегмент – ключ
                if (is_array) *is_array = 0;
                void* val = easy_dict_get(current, seg);
                if (val) return val;
                if (create) {
                    void* new_val = NULL;
                    easy_dict_set(current, seg, &new_val);
                    // возвращаем указатель на новое значение
                    return &new_val;
                }
                return NULL;
            } else {
                // переходим в словарь по ключу
                void* val = easy_dict_get(current, seg);
                if (!val && create) {
                    void* new_val = NULL;
                    easy_dict_set(current, seg, &new_val);
                    val = &new_val;
                }
                parent = current;
                last_seg = seg;
                last_is_array = 0;
                current = val ? *(void**)val : NULL;
                continue;
            }
        }
        easy_free(seg);
    }
    return NULL;
}

// Создание нового пустого сервера
static DictServer* new_dictserver(char* path) {
    DictServer* ds = easy_alloc(sizeof(DictServer));
    ds->path = path ? easy_str_dup(path) : NULL;
    ds->root = easy_dict_new(8, sizeof(void*));
    return ds;
}

void DictServer_save(DictServer* ds) {
    if (!ds || !ds->path) return;
    easy_str json = easy_dict_to_json(ds->root);
    FILE* f = fopen(ds->path, "w");
    if (f) {
        fputs(json, f);
        fclose(f);
    }
    easy_free(json);
}

// Реализация get-функций
easy_str DictServer_get_str(DictServer* ds, char* path) {
    void* node = get_node(ds, path, 0, NULL);
    if (!node) return NULL;
    // предполагаем, что node указывает на easy_str
    easy_str* s = (easy_str*)node;
    return *s ? easy_str_dup(*s) : NULL;
}

easy_int DictServer_get_int(DictServer* ds, char* path) {
    void* node = get_node(ds, path, 0, NULL);
    if (!node) return 0;
    // предполагаем int*
    int* i = (int*)node;
    return *i;
}

easy_bool DictServer_get_bool(DictServer* ds, char* path) {
    void* node = get_node(ds, path, 0, NULL);
    if (!node) return 0;
    int* b = (int*)node;
    return *b;
}

easy_double DictServer_get_double(DictServer* ds, char* path) {
    void* node = get_node(ds, path, 0, NULL);
    if (!node) return 0.0;
    double* d = (double*)node;
    return *d;
}

easy_dict* DictServer_get_dict(DictServer* ds, char* path) {
    void* node = get_node(ds, path, 0, NULL);
    if (!node) return NULL;
    easy_dict** d = (easy_dict**)node;
    return *d;
}

easy_array* DictServer_get_array(DictServer* ds, char* path) {
    void* node = get_node(ds, path, 0, NULL);
    if (!node) return NULL;
    easy_array** a = (easy_array**)node;
    return *a;
}

// Установка значений (создаёт путь)
void DictServer_set_str(DictServer* ds, char* path, easy_str value) {
    void* node = get_node(ds, path, 1, NULL);
    if (!node) return;
    easy_str* dest = (easy_str*)node;
    if (*dest) easy_free(*dest);
    *dest = value ? easy_str_dup(value) : NULL;
}

void DictServer_set_int(DictServer* ds, char* path, easy_int value) {
    void* node = get_node(ds, path, 1, NULL);
    if (!node) return;
    int* dest = (int*)node;
    *dest = value;
}

void DictServer_set_bool(DictServer* ds, char* path, easy_bool value) {
    void* node = get_node(ds, path, 1, NULL);
    if (!node) return;
    int* dest = (int*)node;
    *dest = value;
}

void DictServer_set_double(DictServer* ds, char* path, easy_double value) {
    void* node = get_node(ds, path, 1, NULL);
    if (!node) return;
    double* dest = (double*)node;
    *dest = value;
}

void DictServer_set_dict(DictServer* ds, char* path, easy_dict* value) {
    void* node = get_node(ds, path, 1, NULL);
    if (!node) return;
    easy_dict** dest = (easy_dict**)node;
    if (*dest) easy_dict_free(*dest);
    // Создаём копию словаря (нужна функция easy_dict_copy)
    // Пока просто сохраняем ссылку (осторожно!)
    *dest = value; // владение передаётся серверу? Лучше копировать.
    // Для упрощения пусть будет ссылка.
}

void DictServer_set_array(DictServer* ds, char* path, easy_array* value) {
    void* node = get_node(ds, path, 1, NULL);
    if (!node) return;
    easy_array** dest = (easy_array**)node;
    if (*dest) easy_array_free(*dest);
    *dest = value;
}

void DictServer_set_null(DictServer* ds, char* path) {
    void* node = get_node(ds, path, 1, NULL);
    if (!node) return;
    // Удаляем значение, установив NULL
    // Но в нашем представлении NULL – это особое значение.
    // Для простоты установим NULL в соответствующем месте.
    // Нужно определить, как хранить NULL. Можно хранить NULL-указатель.
    // В get_node, если значение NULL, оно вернётся как NULL.
    // При установке мы просто кладём NULL.
    // Однако в текущей реализации set_str и др. не поддерживают NULL.
    // Поэтому лучше выделить специальную функцию.
    // Пока оставим заглушку.
}

void DictServer_delete(DictServer* ds, char* path) {
    // Удаление узла по пути. Нужно найти родительский узел и удалить ключ/индекс.
    // Это сложнее. Пока не реализуем.
}

easy_array* DictServer_query(DictServer* ds, char* filter) {
    // Простой поиск – заглушка
    return easy_array_new(0, sizeof(void*));
}

void DictServer_free(DictServer* ds) {
    if (ds) {
        if (ds->path) easy_free(ds->path);
        if (ds->root) easy_dict_free(ds->root);
        easy_free(ds);
    }
}