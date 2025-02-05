<script setup>


// -------------------------- Deprecated! --------------------------



import { httpClient } from "../../api/httpClient"

import { EllipsisVerticalIcon, TrashIcon } from "@heroicons/vue/24/outline"

import Paginator from "primevue/paginator"

import CollectionItem from "./CollectionItem.vue"
import { FieldType } from "../../utils/utils"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["collection_id", "class_name", "is_positive"],
  emits: [],
  inject: ["eventBus"],
  data() {
    return {
      collection: useAppStateStore().collections.find((collection) => collection.id === this.collection_id),
      first_index: 0,
      per_page: 10,
      collection_items: [],
    }
  },
  watch: {
    first_index() {
      this.load_collection_items()
    },
  },
  computed: {
    ...mapStores(useAppStateStore),
    item_count() {
      const class_details = this.collection.actual_classes.find((actual_class) => actual_class.name === this.class_name)
      return class_details[this.is_positive ? "positive_count" : "negative_count"]
    }
  },
  mounted() {
    const that = this
    this.load_collection_items()
    this.eventBus.on("collection_item_added", ({collection_id, class_name, is_positive, created_item}) => {
      if (collection_id === this.collection_id && class_name === this.class_name && is_positive === this.is_positive) {
        this.collection_items.unshift(created_item)
      }
    })
    this.eventBus.on("collection_item_removed", ({collection_id, class_name, collection_item_id}) => {
      if (collection_id === this.collection_id && class_name === this.class_name) {
        const item_index = that.collection_items.findIndex((item) => item.id === collection_item_id)
        that.collection_items.splice(item_index, 1)
      }
    })
  },
  methods: {
    load_collection_items() {
      const that = this
      const body = {
        collection_id: this.collection.id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
        is_positive: this.is_positive,
        offset: this.first_index,
        limit: this.per_page,
      }
      httpClient.post("/org/data_map/get_collection_items", body).then(function (response) {
        that.collection_items = response.data
      })
    },
    remove_collection_item(collection_item_id) {
      const that = this
      const body = {
        collection_item_id: collection_item_id,
      }
      httpClient
        .post("/org/data_map/remove_collection_item", body)
        .then(function (response) {
          const item_index = that.collection_items.findIndex((item) => item.id === collection_item_id)
          that.collection_items.splice(item_index, 1)
          const collection = that.appStateStore.collections.find((collection) => collection.id === that.collection_id)
          const class_details = collection.actual_classes.find((actual_class) => actual_class.name === that.class_name)
          class_details[that.is_positive ? "positive_count" : "negative_count"] -= 1
        })
    },
  },
}
</script>

<template>
  <div>
    <div v-if="collection_items.length">
      <Paginator v-model:first="first_index" :rows="per_page" :total-records="item_count"
        class="mt-[0px]"></Paginator>
      <ul class="mb-2 mt-4">
        <li v-for="item in collection_items" :key="item.id" class="justify-between pb-2">
          <CollectionItem
            :dataset_id="item.dataset_id"
            :item_id="item.item_id"
            :is_positive="item.is_positive"
            :show_remove_button="true"
            @remove="remove_collection_item(item.id)">
          </CollectionItem>
        </li>
      </ul>
      <Paginator v-model:first="first_index" :rows="per_page" :total-records="item_count"
        class="mt-[0px]"></Paginator>
    </div>
    <div v-else class="text-center text-gray-500 mb-2">
      No items yet
    </div>
  </div>
</template>
