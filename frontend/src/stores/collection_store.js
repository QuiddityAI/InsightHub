import { defineStore } from "pinia"
import { inject } from "vue"
import { useToast } from "primevue/usetoast"

import { update_object, CollectionItemLayout } from "../utils/utils"

import { httpClient, djangoClient } from "../api/httpClient"
import { FieldType } from "../utils/utils"

const capitalizeFirstLetter = (val) => {
  if (!val) return val
    return String(val).charAt(0).toUpperCase() + String(val).slice(1);
}

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
      filtered_item_ids: [],
      items_last_retrieved: new Date(2020, 1, 1),
      update_collection_is_scheduled: false,
      saved_search_tasks: [],
      important_words: [],
      important_words_are_loading: false,

      // Pagination
      first_index: 0,
      // per_page: 10,  // is now a getter
      order_by_field: 'date_added',
      order_descending: true,
      show_irrelevant: false,
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
      this.filtered_item_ids = []
      this.items_last_retrieved = new Date(2020, 1, 1)
      this.first_index = 0
      this.order_by_field = 'date_added'
      this.order_descending = true
      this.saved_search_tasks = []
      this.important_words = []
      this.important_words_are_loading = false
      this.eventBus.emit("collection_changed", {collection_id: null, class_name: null})

      const queryParams = new URLSearchParams(window.location.search)
      if (queryParams.get("collection_id") !== null) {
        queryParams.delete("collection_id")
        history.pushState(null, null, "?" + queryParams.toString())
      }
    },
    update_collection({update_items = false, update_columns = []} = {}, on_success = null) {
      if (!this.collection_id) {
        console.error("No collection_id set to update collection for")
        return
      }
      const body = {
        collection_id: this.collection_id,
      }
      httpClient.post("/org/data_map/get_collection", body).then((response) => {
        const agent_was_running = this.collection.agent_is_running
        const previously_running_columns = Array.from(this.collection.columns_with_running_processes)  // copy to remove reference
        let new_collection = response.data
        const old_collection = this.collection
        let items_changed_on_server = true
        if (old_collection) {
          items_changed_on_server = new Date(new_collection.items_last_changed) > new Date(old_collection.items_last_changed)
          // using update_object to update it in-place to keep references to old objects
          // to minimize flicker in the UI due to unneeded updates
          update_object(old_collection, new_collection)
        } else {
          this.collection = new_collection
        }

        // it could be that columns_with_running_processes is already empty but a column was updated before,
        // that is why update_columns needs to be respected
        const columns_to_update = update_columns.concat(this.collection.columns_with_running_processes).concat(previously_running_columns)

        if (update_items) {
          // all items on current page and its columns
          this.load_collection_items()
        } else if (columns_to_update.length > 0) {
          this.load_collection_items(columns_to_update)
        }

        if (this.collection.agent_is_running) {
          this.schedule_update_collection(500)
        }
        if (agent_was_running) {
          this.load_collection_items()
        }
        if (agent_was_running && !this.collection.agent_is_running) {
          this.eventBus.emit("agent_stopped")  // triggers writing task to reload
        }

        if (this.collection.columns_with_running_processes.length > 0) {
          // there are still changes going on, update again in a few seconds:
          // (and those changes might change column titles, thats why the collection and not just the items are updated)
          this.schedule_update_collection(1000)
        }

        if (items_changed_on_server) {
          this.eventBus.emit("collection_items_changed_on_server")
        }

        if (on_success) {
          on_success(new_collection)
        }
      })
    },
    schedule_update_collection(timeout_ms=1000, args, on_success = null) {
      if (this.update_collection_is_scheduled) {
        if (on_success) {
          // if on_success is set, it needs to be called and we should rather call update_collection twice
          setTimeout(() => {
            this.update_collection(args, on_success)
          }, timeout_ms)
        }
        return
      }
      this.update_collection_is_scheduled = true
      setTimeout(() => {
        this.update_collection_is_scheduled = false
        this.update_collection(args, on_success)
      }, timeout_ms)
    },
    set_collection_attributes(updates) {
      const body = {
        collection_id: this.collection_id,
        updates: updates,
      }
      httpClient.post("/org/data_map/set_collection_attributes", body).then((response) => {
        for (const key in updates) {
          this.collection[key] = updates[key]
        }
      })
    },
    commit_notification_emails() {
      this.set_collection_attributes({notification_emails: this.collection.notification_emails})
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
    update_ui_settings(updated_settings, load_items=false) {
      this.collection.ui_settings = {...this.collection.ui_settings, ...updated_settings}
      const body = {
        collection_id: this.collection.id,
        ui_settings: this.collection.ui_settings,
      }
      httpClient
        .post("/api/v1/collections/set_ui_settings", body)
        .then((response) => {
          if (load_items) {
            this.load_collection_items()
          }
        })
    },
    // ------------------
    load_collection_items(only_update_specific_columns=null) {
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
        is_positive: !this.show_irrelevant,
        offset: this.first_index,
        limit: this.per_page,
        order_by: (this.order_descending ? "-" : "") + this.order_by_field,
        include_column_data: true,
      }
      httpClient.post("/org/data_map/get_collection_items", body).then((response) => {
        const items = response.data['items']
        if (only_update_specific_columns) {
          for (const item of items) {
            const existing_item = this.collection_items.find((i) => i.id === item.id)
            if (!existing_item) continue
            for (const column_identifier of only_update_specific_columns) {
              existing_item.column_data[column_identifier] = item.column_data[column_identifier]
            }
          }
        } else {
          this.collection_items = items
          // note the semantic difference between "items changed on server" and "items were last retrieved"
          const items_changed_on_server = new Date(response.data['items_last_changed']) > new Date(this.collection.items_last_changed)
          this.collection.items_last_changed = response.data['items_last_changed']
          this.items_last_retrieved = response.data['items_last_changed']
          this.search_mode = response.data['search_mode']
          this.filtered_count = response.data['filtered_count']
          this.filtered_item_ids = response.data['filtered_item_ids']
          this.eventBus.emit("collection_items_loaded")
          if (items_changed_on_server) {
            this.eventBus.emit("collection_items_changed_on_server")
          }
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
              collection_id: collection_id,
              class_name: class_name,
              collection_item_id: collection_item_id,
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
          this.eventBus.emit("collection_items_changed_on_server")
        })
    },
    remove_items_from_collection(item_ids, show_toast=true) {
      const body = {
        collection_id: this.collection_id,
        item_ids: item_ids,
      }
      httpClient
        .post("/api/v1/map/remove_collection_items", body)
        .then((response) => {
          this.collection.actual_classes = response.data.updated_count_per_class
          for (const item_id of response.data.removed_item_ids) {
            this.eventBus.emit("collection_item_removed", {
              collection_id: this.collection_id,
              class_name: "_default",
              collection_item_id: item_id,
            })
          }
          if (show_toast) {
            this.toast.add({severity: 'success', summary: 'Items removed from collection', detail: 'Items removed from the collection', life: 3000})
          }
          this.eventBus.emit("collection_items_changed_on_server")
        })
    },
    // ------------------
    extract_question(column_id, only_current_page=true, collection_item_id=null, remove_content=false) {
      if (!only_current_page && !confirm("This will process items in the collection. This might be long running and expensive. Are you sure?")) {
        return
      }
      const body = {
        cell_range: {
          column_id: column_id,
          class_name: this.class_name,
          offset: only_current_page ? this.first_index : 0,
          limit: only_current_page ? this.per_page : -1,
          order_by: (this.order_descending ? "-" : "") + this.order_by_field,
          collection_item_id: collection_item_id,  // only_current_page and offset etc. is ignored if this is set
        },
        remove_content: remove_content,
      }
      httpClient.post(`/api/v1/columns/process_column`, body)
      .then((response) => {
        this.collection.columns_with_running_processes = response.data.columns_with_running_processes
        const column_identifier = this.collection.columns.find((column) => column.id === column_id).identifier
        this.update_collection({update_columns: [column_identifier]})
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    remove_results(column_id, only_current_page=true, force=false, on_success=null) {
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
      httpClient.post(`/api/v1/columns/remove_column_data`, body)
      .then((response) => {
        if (on_success) {
          on_success()
        }
        const column_identifier = this.collection.columns.find((column) => column.id === column_id).identifier
        this.update_collection({update_columns: [column_identifier]})
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    // ------------------
    set_item_relevance(collection_item, relevance) {
      const body = {
        collection_item_id: collection_item.id,
        relevance: relevance,
      }
      httpClient
        .post("/org/data_map/set_collection_item_relevance", body)
        .then((response) => {
          collection_item.relevance = relevance
          if (this.search_mode && this.collection.ui_settings.hide_checked_items_in_search) {
            this.load_collection_items()
          }
        })
    },
    approve_relevant_search_results() {
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      httpClient
        .post("/api/v1/search/approve_relevant_search_results", body)
        .then((response) => {
          this.update_collection({update_items: true})
        })
    },
    // ------------------
    add_more_items_from_active_task() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      const go_to_next_page = this.first_index + this.per_page == this.filtered_count
      httpClient
        .post("/api/v1/search/add_more_items_from_active_task", body)
        .then((response) => {
          const new_item_count = response.data.new_item_count
          if (new_item_count > 0) {
            if (go_to_next_page) {
              that.first_index += that.per_page
            }
            that.update_collection({update_items: true})
            // there might be columns that start processing in a few ms, so update again in a few seconds:
            that.schedule_update_collection(500)
          }
        })
    },
    run_previous_search_task() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        wait_for_ms: 200,  // wait in case search task is quick and in that case reduce flickering
      }
      httpClient
        .post("/api/v1/search/run_previous_search_task", body)
        .then((response) => {
          that.update_collection({update_items: true})
        })
    },
    run_search_task_similar_to_item(dataset_and_item_id, title) {
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        search_task: {
          search_type: 'similar_to_item',
          dataset_id: dataset_and_item_id[0],
          user_input: `Similar to: ${title}`,
          query: `Similar to: ${title}`,  // ?
          result_language: null,  // ?
          filters: null,
          ranking_settings: null,
          reference_dataset_id: dataset_and_item_id[0],
          reference_item_id: dataset_and_item_id[1],
          origin_name: title,
          candidates_per_step: 50,  // to show a nice map
        },
        wait_for_ms: 200,  // wait in case search task is quick and in that case reduce flickering
      }
      httpClient
        .post("/api/v1/search/run_search_task", body)
        .then((response) => {
          this.update_collection({update_items: true}, () => {
            this.generate_map()
            this.update_ui_settings({secondary_view: 'map'})
          })
        })
    },
    commit_search_task_execution_settings(task) {
      if (task.run_on_new_items) {
        task.is_saved = true
      }
      const body = {
        task_id: task.id,
        updates: {
          is_saved: task.is_saved,
          run_on_new_items: task.run_on_new_items,
        },
      }
      httpClient
        .post("/api/v1/search/update_search_task_execution_settings", body)
        .then((response) => {
          this.fetch_saved_search_tasks()
          if (this.collection.most_recent_search_task?.id === task.id) {
            update_object(this.collection.most_recent_search_task, task)
          }
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
        .post("/api/v1/workflows/cancel_agent", body)
        .then((response) => {
          that.update_collection({update_items: false})
        })
    },
    // ------------------
    get_existing_projections() {
      this.collection.map_metadata.projections_are_ready = false
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      httpClient
        .post("/api/v1/map/get_existing_projections", body)
        .then((response) => {
          if (!response.data) {
            // no map yet
            return
          }
          const {projections, metadata} = response.data
          this.collection.map_metadata = metadata
          // the following signal is connected to the map state store in MainApp:
          this.eventBus.emit("projections_received", {projections})
          this.get_map_cluster_info()
        })
    },
    generate_map() {
      if (!this.collection.map_metadata?.length) {
        this.collection.map_metadata = {}
      }
      this.collection.map_metadata.projections_are_ready = false
      const body = {
        collection: {
          collection_id: this.collection_id,
          class_name: this.class_name,
        },
        parameters: {},
      }
      httpClient
        .post("/api/v1/map/get_new_map", body)
        .then((response) => {
          const {projections, metadata} = response.data
          this.collection.map_metadata = metadata
          if (!projections) return
          // the following signal is connected to the map state store in MainApp:
          this.eventBus.emit("projections_received", {projections})
          this.get_map_cluster_info()
        })
    },
    get_map_cluster_info() {
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      httpClient
        .post("/api/v1/map/get_cluster_info", body)
        .then((response) => {
          const cluster_info = response.data
          // the following signal is connected to the map state store in MainApp:
          this.eventBus.emit("cluster_info_received", {cluster_info})
        })
    },
    // -----------------------------
    add_filter(filter, on_success=null) {
      const body = {
        collection_id: this.collection_id,
        filter: filter,
      }
      httpClient
        .post("/api/v1/filter/add_filter", body)
        .then((response) => {
          if (filter.uid) {
            this.collection.filters = this.collection.filters.filter((existing_filter) => existing_filter.uid !== filter.uid)
          }
          const new_filter = response.data
          this.collection.filters.push(new_filter)
          this.load_collection_items()
          this.eventBus.emit("collection_filters_changed", {filter_type: new_filter.filter_type})
          if (on_success) {
            on_success(new_filter)
          }
        })
    },
    remove_filter(filter_uid, on_success=null) {
      const filter = this.collection.filters.find((filter) => filter.uid === filter_uid)
      if (!filter) return;
      const body = {
        collection_id: this.collection_id,
        filter_uid: filter_uid,
      }
      httpClient
        .post("/api/v1/filter/remove_filter", body)
        .then((response) => {
          this.collection.filters = this.collection.filters.filter((filter) => filter.uid !== filter_uid)
          this.load_collection_items()
          this.eventBus.emit("collection_filters_changed", {filter_type: filter.filter_type})
          if (on_success) {
            on_success()
          }
        })
    },
    get_value_range(field_name, on_success=null) {
      const body = {
        collection_id: this.collection_id,
        field_name: field_name,
      }
      httpClient
        .post("/api/v1/filter/get_value_range", body)
        .then((response) => {
          if (on_success) {
            on_success(response.data)
          }
        })
    },
    fetch_important_words(item_ids) {
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        item_ids: item_ids,
      }
      this.important_words_are_loading = true
      httpClient
        .post("/api/v1/filter/get_important_words", body)
        .then((response) => {
          this.important_words = response.data.words
          this.important_words_are_loading = false
        })
    },
    // ----------------------------- Groups / Parent - Child relations -----------------------------
    show_group(dataset_id, parent_id, label) {
      const new_settings = {
        dataset_id: dataset_id,
        auto_set_filters: false,
        user_input: '',
        result_language: null,
        retrieval_mode: 'keyword',
        ranking_settings: null,
        related_organization_id: null,
        filters: [
          {
            field: '_parent',
            dataset_id: dataset_id,
            operator: 'is',
            value: parent_id,
            label: label,
          }
        ],
      }
      const body = {
        search_task: new_settings,
        collection_id: this.collection_id,
        class_name: this.class_name,
        wait_for_ms: 200,  // wait in case search task is quick and in that case reduce flickering
      }
      httpClient
        .post("/api/v1/search/run_search_task", body)
        .then((response) => {
          this.update_collection({update_items: true})
        })
    },
    // ----------------------------- Saved / Periodic Search Tasks -----------------------------
    fetch_saved_search_tasks() {
      const body = {
        collection_id: this.collection_id,
      }
      httpClient
        .post("/api/v1/search/get_saved_search_tasks", body)
        .then((response) => {
          this.saved_search_tasks = response.data["tasks"]
        })
    },
    run_existing_search_task(task_id) {
      const body = {
        task_id: task_id,
      }
      httpClient
        .post("/api/v1/search/run_existing_search_task", body)
        .then((response) => {
          this.update_collection({update_items: true})
        })
    },
    test_notification_email({run_on_current_candidates = false} = {}) {
      const body = {
        collection_id: this.collection_id,
        run_on_current_candidates: run_on_current_candidates,
      }
      httpClient
        .post("/api/v1/search/test_notification_email", body)
        .then((response) => {
          this.toast.add({severity: 'success', summary: 'Test email sent', detail: 'Test email sent', life: 3000})
        })
    },
  },
  getters: {
    item_count() {
      const class_details = this.collection.actual_classes.find((actual_class) => actual_class.name === this.class_name)
      return class_details["positive_count"]
    },
    per_page: (state) => {
      return state.collection?.ui_settings?.item_layout === CollectionItemLayout.SPREADSHEET ? 30 : 10
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
          name: `${$t('general.column')}: ${column.name}`,
        }
      }
      available_fields['_descriptive_text_fields'] = {
        identifier: '_descriptive_text_fields',
        name: $t('general.descriptive-text-fields-long'),
      }
      available_fields['_full_text_snippets'] = {
        identifier: '_full_text_snippets',
        name: $t('general.full-text-excerpts')
      }
      return Object.values(available_fields).sort((a, b) => a.identifier.localeCompare(b.identifier))
    },
    language(state) {
      return navigator.language.split('-')[0]
    },
    entity_name_singular(state) {
      const first_dataset_id = state.collection_items.length ? state.collection_items[0].dataset_id : null
      if (!first_dataset_id) return null
      const schema = window.appState.datasets[first_dataset_id]?.schema
      const n = schema ? schema.translated_entity_name.singular[this.language] || schema.entity_name : null
      return capitalizeFirstLetter(n)
    },
    entity_name_plural(state) {
      const first_dataset_id = state.collection_items.length ? state.collection_items[0].dataset_id : null
      if (!first_dataset_id) return null
      const schema = window.appState.datasets[first_dataset_id]?.schema
      const n = schema ? schema.translated_entity_name.plural[this.language] || schema.entity_name_plural : null
      return capitalizeFirstLetter(n)
    },
  },
})
