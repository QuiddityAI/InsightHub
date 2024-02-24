<script setup>
import httpClient from "../../api/httpClient"

import { EllipsisVerticalIcon, TrashIcon } from "@heroicons/vue/24/outline"

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
      examples: [],
    }
  },
  watch: {},
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
    const that = this
    this.load_examples(this.is_positive)
    this.eventBus.on("collection_item_added", ({collection_id, class_name, is_positive, created_item}) => {
      if (collection_id === this.collection_id && class_name === this.class_name && is_positive === this.is_positive) {
        this.examples.unshift(created_item)
      }
    })
    this.eventBus.on("collection_item_removed", ({collection_id, class_name, collection_item_id}) => {
      if (collection_id === this.collection_id && class_name === this.class_name) {
        const item_index = that.examples.findIndex((item) => item.id === collection_item_id)
        that.examples.splice(item_index, 1)
      }
    })
  },
  methods: {
    load_examples(is_positive) {
      const that = this
      const body = {
        collection_id: this.collection.id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
        is_positive: is_positive,
      }
      httpClient.post("/org/data_map/get_collection_items", body).then(function (response) {
        that.examples = response.data
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
          const item_index = that.examples.findIndex((item) => item.id === collection_item_id)
          that.examples.splice(item_index, 1)
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
    <ul class="mb-2 mt-4">
      <li v-for="example in examples" :key="example.id" class="justify-between pb-2">
        <CollectionItem
          :dataset_id="JSON.parse(example.value)[0]"
          :item_id="JSON.parse(example.value)[1]"
          :is_positive="example.is_positive"
          @remove="remove_collection_item(example.id)">
        </CollectionItem>
      </li>
    </ul>
  </div>
</template>
