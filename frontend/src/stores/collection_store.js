import { defineStore } from "pinia"
import { inject } from "vue"

import { httpClient, djangoClient } from "../api/httpClient"
import { FieldType } from "../utils/utils"

export const useCollectionStore = defineStore("collection", {
  state: () => {
    return {
      eventBus: inject("eventBus"),
      appStateStore: inject("appState"),
      collection_id: null,
      class_name: null,
      available_collections: [],

      // The following are used to store the current collection's data
      collection: null,
      collection_items: null,
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
  },
  getters: {
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
      return Array.from(dataset_ids).map((dataset_id) => this.appStateStore.datasets[dataset_id])
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