<script setup>
import httpClient from "../../api/httpClient"

import {
  ChevronLeftIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"

import ClassifierExampleList from "./ClassifierExampleList.vue"
import { FieldType } from "../../utils/utils"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["classifier_id", "class_name"],
  emits: ["close"],
  data() {
    return {
      selected_tab: "positives",
      classifier: useAppStateStore().classifiers.find((classifier) => classifier.id === this.classifier_id),
      positive_examples: [],
      negative_examples: [],
    }
  },
  watch: {
    selected_tab() {
      if (this.selected_tab === "negatives") {
        this.load_examples(/* is_positive */ false)
      }
    },
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.load_examples(/* is_positive */ true)
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
        if (is_positive) {
          that.positive_examples = response.data
        } else {
          that.negative_examples = response.data
        }
      })
    },
    delete_classifier_class() {
      if (!confirm("Are you sure you want to delete this class and the list of examples?")) {
        return
      }
      const that = this
      const body = {
        classifier_id: this.classifier_id,
        class_name: this.class_name,
      }
      httpClient
        .post("/org/data_map/delete_classifier_class", body)
        .then(function (response) {
          const index = that.classifier.actual_classes.findIndex((classifier_class) => classifier_class.name === that.class_name)
          that.classifier.actual_classes.splice(index, 1)
          if (that.classifier.actual_classes.length === 0) {
            that.classifier.actual_classes.push({
              name: "_default",
              positive_count: 0,
              negative_count: 0,
            })
          }
        })
      this.$emit("close")
    },
  },
}
</script>

<template>
  <div>
    <div class="mb-3 ml-1 mt-3 flex flex-row gap-3">
      <button
        @click="$emit('close')"
        class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
        <ChevronLeftIcon></ChevronLeftIcon>
      </button>
      <span class="font-bold text-gray-600">{{ classifier.name }}:</span>
      <span class="text-medium text-gray-500">
        {{ class_name === '_default' ? 'Items' : class_name }} </span>

      <div class="flex-1"></div>

      <button
        @click="delete_classifier_class"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
    </div>

    <div
      class="flex flex-row items-center justify-between text-center font-bold text-gray-400">
      <button
        v-for="item in [['positives', '+'], ['negatives', '-'], ['learn', 'Learn'], ['recommend', 'Recom.']]"
        class="flex-1"
        :class="{'text-blue-500': selected_tab === item[0]}"
        @click="selected_tab = item[0]">
        {{ item[1] }}
      </button>
    </div>
    <hr />

    <ClassifierExampleList
      v-if="selected_tab === 'positives'"
      :is_positive="true"
      :classifier_id="classifier_id"
      :class_name="class_name">
    </ClassifierExampleList>

    <ClassifierExampleList
      v-if="selected_tab === 'negatives'"
      :is_positive="false"
      :classifier_id="classifier_id"
      :class_name="class_name">
    </ClassifierExampleList>

    <div v-if="selected_tab === 'learn'">Learn</div>

    <div v-if="selected_tab === 'recommend'">Rec</div>

  </div>
</template>
