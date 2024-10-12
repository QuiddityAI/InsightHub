import { defineStore } from "pinia"
import { inject } from "vue"
import { useToast } from "primevue/usetoast"

import { update_object } from "../utils/utils"

import { httpClient, djangoClient } from "../api/httpClient"
import { FieldType } from "../utils/utils"

export const useCollectionStore = defineStore("collection", {
  state: () => {
    return {
      eventBus: inject("eventBus"),
      toast: useToast(),

      available_collections: [],

      collection_id: null,
      class_name: null,
      is_positive: true,  // deprecated

      // The following are used to store the current collection's data
      collection: null,
      collection_items: null,
      search_mode: false,
      filtered_count: null,
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
          that.check_url_parameters()
        })
    },
    check_url_parameters() {
      if (!this.available_collections.length) return
      const queryParams = new URLSearchParams(window.location.search)
      if (queryParams.get("collection_id") !== null) {
        this.open_collection(parseInt(queryParams.get("collection_id")))
      } else {
        this.close_collection()
      }
    },
    open_collection(collection_id, class_name=null) {
      class_name = class_name || '_default'
      if (this.collection_id) {
        this.close_collection()
        setTimeout(() => {
          this.open_collection(collection_id, class_name)
        }, 0)
        return
      }
      this.collection_id = collection_id
      this.class_name = class_name
      this.collection_items = []
      this.collection = this.available_collections.find((c) => c.id === collection_id)
      this.eventBus.emit("collection_changed", {collection_id, class_name})

      const queryParams = new URLSearchParams(window.location.search)
      if (queryParams.get("collection_id") !== collection_id.toString()) {
        queryParams.set("collection_id", collection_id)
        history.pushState(null, null, "?" + queryParams.toString())
      }
    },
    close_collection() {
      this.collection_id = null
      this.class_name = null
      this.collection = null
      this.collection_items = []
      this.search_mode = false
      this.filtered_count = null
      this.items_last_updated = new Date(2020, 1, 1)
      this.first_index = 0
      this.per_page = 10
      this.order_by_field = 'date_added'
      this.order_descending = true
      this.eventBus.emit("collection_changed", {collection_id: null, class_name: null})

      const queryParams = new URLSearchParams(window.location.search)
      if (queryParams.get("collection_id") !== null) {
        queryParams.delete("collection_id")
        history.pushState(null, null, "?" + queryParams.toString())
      }
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
          // using update_object to update it in-place to keep references to old objects
          // to minimize flicker in the UI due to unneeded updates
          update_object(old_collection, new_collection)
        } else {
          that.collection = new_collection
        }
        if (on_success) {
          on_success(new_collection)
        }
      })
    },
    check_for_agent_status() {
      const that = this
      if (this.collection.agent_is_running) {
        setTimeout(() => {
          that.update_collection((collection) => {
            that.load_collection_items()
            if (collection.agent_is_running) {
              that.check_for_agent_status()
            } else {
              // agent has stopped
              that.eventBus.emit("agent_stopped")  // triggers writing task to reload
              for (let column_identifier of collection.columns_with_running_processes) {
                 // TODO: this could be more elegant
                const column_id = that.collection.columns.find((column) => column.identifier === column_identifier).id
                that.get_extraction_results(column_id)
              }
            }
          })
        }, 500)
      }
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
          that.filtered_count = response.data['filtered_count']
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
    extract_question(column_id, only_current_page=true) {
      const that = this
      if (!only_current_page && !confirm("This will extract the question for all items in the collection. This might be long running and expensive. Are you sure?")) {
        return
      }
      const body = {
        column_id: column_id,
        class_name: this.class_name,
        offset: only_current_page ? this.first_index : 0,
        limit: only_current_page ? this.per_page : -1,
        order_by: (this.order_descending ? "-" : "") + this.order_by_field,
      }
      httpClient.post(`/org/data_map/extract_question_from_collection_class_items`, body)
      .then(function (response) {
        that.collection.columns_with_running_processes = response.data.columns_with_running_processes
        that.get_extraction_results(column_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    get_extraction_results(column_id) {
      const that = this
      const column_identifier = this.collection.columns.find((column) => column.id === column_id).identifier
      this.load_collection_items([column_identifier])
      this.update_collection(() => {
        // if (JSON.stringify(response.data.columns) !== JSON.stringify(that.collection.columns)) {
        //   that.collection.columns = response.data.columns
        // }
        // that.collection.columns_with_running_processes = response.data.columns_with_running_processes
        if (this.collection.columns_with_running_processes.includes(column_identifier)) {
          setTimeout(() => {
            this.get_extraction_results(column_id)
          }, 1000)
        }
      })
    },
    remove_results(column_id, only_current_page=true, force=false, on_success=null) {
      const that = this
      if (!only_current_page && !force && !confirm("This will remove the column content for all items in the collection. Are you sure?")) {
        return
      }
      const body = {
        column_id: column_id,
        class_name: this.class_name,
        offset: only_current_page ? this.first_index : 0,
        limit: only_current_page ? this.per_page : -1,
        order_by: (this.order_descending ? "-" : "") + this.order_by_field,
      }
      httpClient.post(`/org/data_map/remove_collection_class_column_data`, body)
      .then(function (response) {
        if (on_success) {
          on_success()
        }
        that.get_extraction_results(column_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    // ------------------
    set_item_relevance(collection_item, relevance) {
      const that = this
      const body = {
        collection_item_id: collection_item.id,
        relevance: relevance,
      }
      httpClient
        .post("/org/data_map/set_collection_item_relevance", body)
        .then((response) => {
          collection_item.relevance = relevance
        })
    },
    // ------------------
    add_items_from_active_sources() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      const go_to_next_page = this.first_index + this.per_page == this.item_count
      httpClient
        .post("/api/v1/search/add_items_from_active_sources", body)
        .then((response) => {
          const new_item_count = response.data.new_item_count
          if (new_item_count > 0) {
            if (go_to_next_page) {
              that.first_index += that.per_page
            }
            that.update_collection(() => {
              that.load_collection_items()
            })
          }
        })
    },
    run_search_task_similar_to_item(dataset_and_item_id, title) {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        search_task: {
          search_type: 'similar_to_item',
          dataset_id: dataset_and_item_id[0],
          query: `Similar to: ${title}`,  // ?
          result_language: null,  // ?
          filters: null,
          ranking_settings: null,
          reference_dataset_id: dataset_and_item_id[0],
          reference_item_id: dataset_and_item_id[1],
          origin_name: title,
        },
      }
      httpClient
        .post("/api/v1/search/run_search_task", body)
        .then((response) => {
          that.update_collection(() => {
            that.check_for_agent_status()
            that.load_collection_items()
          })
        })
    },
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
    cancel_agent() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      httpClient
        .post("/api/v1/preparation/cancel_agent", body)
        .then((response) => {
          that.update_collection()
        })
    }
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
      available_fields['changed_at'] = {
        identifier: 'changed_at',
        name: 'Last Changed',
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