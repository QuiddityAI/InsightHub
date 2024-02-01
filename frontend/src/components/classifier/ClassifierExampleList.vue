<script setup>
import httpClient from "../../api/httpClient"

import { EllipsisVerticalIcon, TrashIcon } from "@heroicons/vue/24/outline"

import ClassifierExample from "./ClassifierExample.vue"
import { FieldType } from "../../utils/utils"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/settings_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["classifier_id", "class_name", "is_positive"],
  emits: [],
  data() {
    return {
      classifier: useAppStateStore().classifiers.find((classifier) => classifier.id === this.classifier_id),
      examples: [],
    }
  },
  watch: {},
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.load_examples(this.is_positive)
  },
  methods: {
    load_examples(is_positive) {
      const that = this
      const body = {
        classifier_id: this.classifier.id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
        is_positive: is_positive,
      }
      httpClient.post("/org/data_map/get_classifier_examples", body).then(function (response) {
        that.examples = response.data
      })
    },
    remove_classifier_example(classifier_example_id) {
      const that = this
      const body = {
        classifier_example_id: classifier_example_id,
      }
      httpClient
        .post("/org/data_map/remove_classifier_example", body)
        .then(function (response) {
          const item_index = that.examples.findIndex((item) => item.id === classifier_example_id)
          that.examples.splice(item_index, 1)
        })
    },
  },
}
</script>

<template>
  <div>
    <ul class="mb-2 mt-4">
      <li v-for="example in examples" :key="example.id" class="justify-between pb-2">
        <ClassifierExample
          :item_id="example.value"
          :is_positive="example.is_positive"
          @remove="remove_classifier_example(example.id)">
        </ClassifierExample>
      </li>
    </ul>
  </div>
</template>
