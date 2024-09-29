import { defineStore } from "pinia"
import { inject } from "vue"
import { useToast } from "primevue/usetoast"

import { httpClient, djangoClient } from "../api/httpClient"
import { FieldType } from "../utils/utils"

export const useCollectionStore = defineStore("collection", {
  state: () => {
    return {
      eventBus: inject("eventBus"),
      toast: useToast(),
      collection_id: null,
      class_name: null,
      available_collections: [],
      is_positive: true,

      // The following are used to store the current collection's data
      collection: null,
      collection_items: null,
      search_mode: false,
      items_last_updated: new Date(2020, 1, 1),

      // Pagination
      first_index: 0,
      per_page: 10,
      order_by_field: 'date_added',
      order_descending: true,
    }
  },
  actions: {
    get_available_collections(organization_id) {
      const that = this
      this.available_collections = []
      const get_collections_body = {
        related_organization_id: organization_id,
      }
      httpClient
        .post("/org/data_map/get_collections", get_collections_body)
        .then(function (response) {
          that.available_collections = response.data || []
        })
    },
    open_collection(collection_id, class_name) {
      if (this.collection_id) {
        this.close_collection()
        setTimeout(() => {
          this.collection_id = collection_id
          this.class_name = class_name
          this.collection_items = []
          this.collection = this.available_collections.find((c) => c.id === collection_id)
          this.eventBus.emit("collection_changed", {collection_id, class_name})
        }, 0)
      } else {
        this.collection_id = collection_id
        this.class_name = class_name
        this.collection_items = []
        this.collection = this.available_collections.find((c) => c.id === collection_id)
        this.eventBus.emit("collection_changed", {collection_id, class_name})
      }
    },
    close_collection() {
      this.collection_id = null
      this.class_name = null
      this.collection = null
      this.collection_items = []
      this.eventBus.emit("collection_changed", {collection_id: null, class_name: null})
    },
    update_collection(on_success = null) {
      if (!this.collection_id) {
        return
      }
      const that = this
      const body = {
        collection_id: this.collection_id,
      }
      httpClient.post("/org/data_map/get_collection", body).then(function (response) {
        let new_collection = response.data
        const old_collection = that.collection
        if (old_collection) {
          for (let key in new_collection) {
            old_collection[key] = new_collection[key]
          }
        } else {
          that.collection = new_collection
        }
        if (on_success) {
          on_success(new_collection)
        }
      })
    },
    delete_collection(collection_id) {
      const that = this
      const delete_collection_body = {
        collection_id: collection_id,
      }
      httpClient
        .post("/org/data_map/delete_collection", delete_collection_body)
        .then(function (response) {
          const index = that.available_collections.findIndex((collection) => collection.id === that.collection_id)
          that.available_collections.splice(index, 1)
          if (that.collection_id === collection_id) {
            that.close_collection()
          }
        })
    },
    // ------------------
    load_collection_items(only_update_specific_columns=null) {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
        is_positive: true,
        offset: this.first_index,
        limit: this.per_page,
        order_by: (this.order_descending ? "-" : "") + this.order_by_field,
        include_column_data: true,
      }
      httpClient.post("/org/data_map/get_collection_items", body).then(function (response) {
        const items = response.data['items']
        if (only_update_specific_columns) {
          for (const item of items) {
            const existing_item = that.collection_items.find((i) => i.id === item.id)
            if (!existing_item) continue
            for (const column_identifier of only_update_specific_columns) {
              existing_item.column_data[column_identifier] = item.column_data[column_identifier]
            }
          }
        } else {
          that.collection_items = items
          that.items_last_updated = response.data['items_last_changed']
          that.search_mode = response.data['search_mode']
        }
      })
    },
    add_item_to_collection(ds_and_item_id, collection_id, class_name, is_positive, show_toast=true) {
      const that = this
      this.last_used_collection_id = collection_id
      this.last_used_collection_class = class_name
      const add_item_to_collection_body = {
        collection_id: collection_id,
        is_positive: is_positive,
        class_name: class_name,
        field_type: FieldType.IDENTIFIER,
        value: null,
        dataset_id: ds_and_item_id[0],
        item_id: ds_and_item_id[1],
        weight: 1.0,
      }
      httpClient
        .post("/org/data_map/add_item_to_collection", add_item_to_collection_body)
        .then(function (created_item) {
          const collection = that.available_collections.find((collection) => collection.id === collection_id)
          if (!collection) return
          const class_details = collection.actual_classes.find(
            (actual_class) => actual_class.name === class_name
          )
          class_details[is_positive ? "positive_count" : "negative_count"] += 1
          that.eventBus.emit("collection_item_added", {
            collection_id: collection.id,
            class_name,
            is_positive,
            created_item: created_item.data,
          })
          if (show_toast) {
            that.toast.add({severity: 'success', summary: 'Item added to collection', detail: 'Item added to the collection', life: 3000})
          }
        })
    },
    remove_item_from_collection(ds_and_item_id, collection_id, class_name, show_toast=true) {
      const that = this
      const body = {
        collection_id: collection_id,
        class_name: class_name,
        value: null,
        dataset_id: ds_and_item_id[0],
        item_id: ds_and_item_id[1],
      }
      httpClient
        .post("/org/data_map/remove_collection_item_by_value", body)
        .then(function (response) {
          for (const item of response.data) {
            const collection_item_id = item.id
            that.eventBus.emit("collection_item_removed", {
              collection_id,
              class_name,
              collection_item_id,
            })
            const collection = that.available_collections.find(
              (collection) => collection.id === collection_id
            )
            const class_details = collection.actual_classes.find(
              (actual_class) => actual_class.name === class_name
            )
            class_details[item.is_positive ? "positive_count" : "negative_count"] -= 1
          }
          if (show_toast) {
            that.toast.add({severity: 'success', summary: 'Item removed from collection', detail: 'Item removed from the collection', life: 3000})
          }
        })
    },
    // ------------------
    exit_search_mode() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      httpClient
        .post("/api/v1/search/exit_search_mode", body)
        .then((response) => {
          this.search_mode = false
          this.load_collection_items()
        })
    },
  },
  getters: {
    item_count() {
      const class_details = this.collection.actual_classes.find((actual_class) => actual_class.name === this.class_name)
      return class_details["positive_count"]
    },
    available_order_by_fields(state) {
      const available_fields = {}
      for (const column of state.collection.columns) {
        available_fields[column.identifier] = {
          identifier: 'column_data__' + column.identifier + '__value',
          name: column.name,
        }
      }
      available_fields['date_added'] = {
        identifier: 'date_added',
        name: 'Date Added',
      }
      available_fields['changed_at'] = {
        identifier: 'changed_at',
        name: 'Last Changed',
      }
      return Object.values(available_fields)
    },
    included_datasets(state) {
      const dataset_ids = new Set()
      for (const item of state.collection_items) {
        const dataset_id = item.dataset_id
        dataset_ids.add(dataset_id)
      }
      return Array.from(dataset_ids).map((dataset_id) => window.appState.datasets[dataset_id])
    },
    available_source_fields(state) {
      const available_fields = {}
      const unsupported_field_types = [FieldType.VECTOR, FieldType.CLASS_PROBABILITY, FieldType.ARBITRARY_OBJECT]
      function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
      }
      for (const dataset of state.included_datasets) {
        if (!dataset?.schema?.object_fields) continue
        for (const field of Object.values(dataset.schema.object_fields)) {
          if (unsupported_field_types.includes(field.field_type)) {
            continue
          }
          available_fields[field.identifier] = {
            identifier: field.identifier,
            name: `${capitalizeFirstLetter(dataset.schema.entity_name)}: ${field.name || field.identifier}`,
          }
        }
      }
      for (const column of state.collection.columns) {
        available_fields[column.identifier] = {
          identifier: '_column__' + column.identifier,
          name: `Column: ${column.name}`,
        }
      }
      available_fields['_descriptive_text_fields'] = {
        identifier: '_descriptive_text_fields',
        name: 'All short descriptive text fields',
      }
      available_fields['_full_text_snippets'] = {
        identifier: '_full_text_snippets',
        name: 'Full text excerpts',
      }
      return Object.values(available_fields).sort((a, b) => a.identifier.localeCompare(b.identifier))
    },
  },
})