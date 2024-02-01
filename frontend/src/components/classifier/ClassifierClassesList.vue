<script setup>
import httpClient from "../../api/httpClient"

import {
  ChevronLeftIcon,
  TrashIcon
} from "@heroicons/vue/24/outline"

import ClassifierClassListItem from "./ClassifierClassListItem.vue"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/settings_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["classifier_id"],
  emits: ["classifier_selected", "class_selected", "close"],
  data() {
    return {
      classifier: useAppStateStore().classifiers.find((classifier) => classifier.id === this.classifier_id),
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {},
  methods: {
    delete_classifier() {
      if (!confirm("Are you sure you want to delete this classifier?")) {
        return
      }
      const that = this
      const delete_classifier_body = {
        classifier_id: this.classifier_id,
      }
      httpClient
        .post("/org/data_map/delete_classifier", delete_classifier_body)
        .then(function (response) {
          const index = that.appStateStore.classifiers.findIndex((classifier) => classifier.id === that.classifier_id)
          that.appStateStore.classifiers.splice(index, 1)
        })
      this.$emit("close")
    },
    create_classifier_class(class_name) {
      if (!class_name) {
        return
      }
      const that = this
      const body = {
        classifier_id: this.classifier_id,
        class_name: class_name,
      }
      httpClient
        .post("/org/data_map/add_classifier_class", body)
        .then(function (response) {
          that.classifier.actual_classes.push({
            name: class_name,
            positive_count: 0,
            negative_count: 0,
          })
        })
    },
  },
}
</script>

<template>
  <div>
    <div class="mb-3 ml-1 mt-3 flex flex-row gap-3">
      <button @click="$emit('close')" class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
        <ChevronLeftIcon></ChevronLeftIcon>
      </button>
      <span class="font-bold text-gray-600">{{ classifier.name }}</span>

      <div class="flex-1"></div>

      <button
        @click="delete_classifier"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
    </div>

    <!-- <div v-if="settings_visible" class="mt-2 flex flex-row gap-3">
      <button
        @click="train_classifier"
        class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Train Classifier
      </button>
      <button @click="" class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        X: highlight similar in map
      </button>
      <button @click="" class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Color: xxx
      </button>
      <button @click="" class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Symbol: xxx
      </button>
    </div> -->

    <div class="my-2 flex items-stretch">
      <input
        ref="new_classifier_name"
        type="text"
        class="flex-auto rounded-l-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        placeholder="Class Name"
        @keyup.enter="create_classifier_class($refs.new_classifier_name.value); $refs.new_classifier_name.value = ''"/>
      <button
        class="rounded-r-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="create_classifier_class($refs.new_classifier_name.value); $refs.new_classifier_name.value = ''">
        Create
      </button>
    </div>

    <ul class="mt-3">
      <ClassifierClassListItem
        v-for="class_details in classifier.actual_classes"
        :key="class_details.name"
        :class_details="class_details"
        @click="$emit('class_selected', class_details.name); $emit('classifier_selected', classifier.id)">
      </ClassifierClassListItem>
    </ul>

    <div
      v-if="classifier.actual_classes.length === 0"
      class="flex h-20 flex-col place-content-center text-center">
      <p class="flex-none text-gray-400">No Classes Yet</p>
    </div>
  </div>
</template>
